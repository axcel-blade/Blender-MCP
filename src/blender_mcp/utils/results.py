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
