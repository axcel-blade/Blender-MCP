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


def _jsonable(value: Any, depth: int = 0) -> Any:
    """Best-effort conversion of bpy/mathutils values into JSON-safe data."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if depth > 6:
        return repr(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v, depth + 1) for v in value]
    name = getattr(value, "name", None)
    if isinstance(name, str) and hasattr(value, "bl_rna"):
        return {"type": type(value).__name__, "name": name}
    try:  # mathutils Vector/Color/Euler/Quaternion/Matrix
        return [_jsonable(v, depth + 1) for v in value]
    except TypeError:
        return repr(value)


def run_script(code: str) -> Any:
    """Run ``code`` in ONE namespace (so functions see top-level names) with bpy preloaded.

    The result is the ``result`` variable if the script sets one, otherwise the value of
    a trailing expression (REPL semantics), otherwise None.
    """
    import ast

    namespace: dict[str, Any] = {"__name__": "__blender_mcp__"}
    try:
        import bpy  # noqa: F401
        import mathutils  # noqa: F401

        namespace.update({"bpy": bpy, "mathutils": mathutils, "C": bpy.context, "D": bpy.data})
    except ImportError:  # running outside Blender (tests)
        pass

    tree = ast.parse(code, filename="<blender_mcp>", mode="exec")
    tail = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        tail = ast.Expression(tree.body.pop().value)
    exec(compile(tree, "<blender_mcp>", "exec"), namespace)  # noqa: S102
    value = None
    if tail is not None:
        value = eval(compile(tail, "<blender_mcp>", "eval"), namespace)  # noqa: S307
    if "result" in namespace:
        value = namespace["result"]
    elif "__result__" in namespace:
        value = namespace["__result__"]
    return _jsonable(value)


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
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result_value = run_script(code)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        # Keep only frames from the user's script so the model sees its own line numbers.
        frames = [
            f for f in traceback.extract_tb(exc.__traceback__) if f.filename == "<blender_mcp>"
        ]
        tb = "".join(traceback.format_list(frames)) + "".join(
            traceback.format_exception_only(type(exc), exc)
        )
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
