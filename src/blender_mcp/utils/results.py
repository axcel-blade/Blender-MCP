"""Helpers for normalizing tool results."""

from __future__ import annotations

from typing import Any

from blender_mcp.exceptions import BlenderMCPError


def ok(result: Any = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"success": True, "result": result}
    payload.update(extra)
    return payload


def fail_from_exception(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, BlenderMCPError):
        return exc.to_dict()
    return {
        "success": False,
        "error_code": "OPERATION_FAILED",
        "error": str(exc),
        "details": {},
    }


# Text output budgets. Every tool reply stays in the model's context and is re-sent on
# each later turn, so runaway prints or huge return values cost tokens for the whole
# session. Head and tail are kept because errors and summaries tend to sit at the end.
MAX_STREAM_CHARS = 4000
MAX_RESULT_CHARS = 8000


def clip_text(text: Any, limit: int) -> Any:
    """Keep the head and tail of a long string, noting how much was dropped."""
    if not isinstance(text, str) or len(text) <= limit:
        return text
    head = limit * 2 // 3
    tail = limit - head
    dropped = len(text) - head - tail
    return f"{text[:head]}\n... [{dropped} chars omitted] ...\n{text[-tail:]}"


def compact_script_result(payload: Any) -> Any:
    """Bound the size of an execute_blender_code reply (envelope ``{"result": entry}``)."""
    import json

    entry = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(entry, dict) or "stdout" not in entry:
        return payload
    for key in ("stdout", "stderr", "traceback"):
        entry[key] = clip_text(entry.get(key), MAX_STREAM_CHARS)
    for key in ("stdout", "stderr", "traceback", "error"):
        if entry.get(key) in ("", None):
            entry.pop(key, None)
    if isinstance(entry.get("duration_ms"), float):
        entry["duration_ms"] = round(entry["duration_ms"], 1)
    value = entry.get("result")
    try:
        encoded = json.dumps(value, default=str)
    except (TypeError, ValueError):
        encoded = str(value)
    if len(encoded) > MAX_RESULT_CHARS:
        entry["result"] = clip_text(encoded, MAX_RESULT_CHARS)
        entry["result_truncated"] = (
            f"Result was {len(encoded)} chars as JSON; return only the fields you need."
        )
    return payload


def _strip_images(value: Any, images: list[str]) -> Any:
    """Recursively pull ``image_base64`` payloads out of a result, collecting them."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key == "image_base64":
                if item:
                    images.append(item)
                    out["image_index"] = len(images) - 1
                continue
            out[key] = _strip_images(item, images)
        return out
    if isinstance(value, list):
        return [_strip_images(item, images) for item in value]
    return value


def to_image_content(payload: dict[str, Any]) -> list[Any]:
    """Convert a bridge result holding base64 PNGs into MCP text + image content blocks.

    Returning real ``ImageContent`` lets the model actually see the viewport instead of
    receiving an opaque base64 string inside JSON.
    """
    import json

    from mcp.types import ImageContent, TextContent

    images: list[str] = []
    summary = _strip_images(payload, images)
    blocks: list[Any] = [TextContent(type="text", text=json.dumps(summary, default=str))]
    for data in images:
        blocks.append(ImageContent(type="image", data=data, mimeType="image/png"))
    return blocks
