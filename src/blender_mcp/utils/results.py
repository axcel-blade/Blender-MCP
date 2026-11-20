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
