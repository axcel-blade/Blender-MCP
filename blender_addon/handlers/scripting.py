"""Arbitrary Blender Python execution handler."""

from __future__ import annotations

import io
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from . import command

_HISTORY: list[dict[str, Any]] = []


def _prefs():
    from ..utils.prefs import get_preferences

    return get_preferences()


@command("execute_blender_code")
def execute_blender_code(params: dict[str, Any]):
    prefs = _prefs()
    mode = getattr(prefs, "script_permission", "trusted") if prefs else "trusted"
    safe = getattr(prefs, "safe_execution_mode", True) if prefs else True
    code = params.get("code") or ""
    preview_only = bool(params.get("preview_only", False))
    confirmed = bool(params.get("confirmed", False))

    if safe and mode == "restricted":
        raise PermissionError(
            "Script execution disabled (script_permission=restricted). "
            "Change addon preferences to confirmation or trusted."
        )
    if mode == "confirmation" and not preview_only and not confirmed:
        raise PermissionError("confirmation mode requires confirmed=true after preview")
    if mode == "restricted":
        raise PermissionError("Script execution is restricted")

    if preview_only:
        return {
            "preview_only": True,
            "code": code,
            "warning": (
                "This will run arbitrary Python inside Blender with access to files, "
                "network, and process capabilities available to Blender. Not a sandbox."
            ),
        }

    stdout = io.StringIO()
    stderr = io.StringIO()
    started = time.time()
    result_value = None
    error = None
    tb = None
    try:
        local_ns: dict[str, Any] = {}
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(code, {"__name__": "__blender_mcp__"}, local_ns)  # noqa: S102
            result_value = local_ns.get("result", local_ns.get("__result__"))
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        tb = traceback.format_exc()
    duration_ms = (time.time() - started) * 1000.0
    entry = {
        "success": error is None,
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "result": result_value,
        "error": error,
        "traceback": tb,
        "duration_ms": duration_ms,
    }
    _HISTORY.append({"code": code[:500], **entry})
    if len(_HISTORY) > 50:
        del _HISTORY[:-50]
    if error:
        return {
            "success": False,
            "error_code": "SCRIPT_EXECUTION_FAILED",
            "error": error,
            "details": entry,
        }
    return entry
