"""Command dispatch for Blender MCP handlers."""

from __future__ import annotations

import collections
import importlib
import sys
import time
from collections.abc import Callable
from typing import Any

Handler = Callable[[dict[str, Any]], Any]
_REGISTRY: dict[str, Handler] = {}

# Execution log for get_execution_history (bounded; survives handler reloads via sys.modules).
_HISTORY: collections.deque = collections.deque(maxlen=500)
# Commands that only read state: no undo step is pushed for them.
_READ_ONLY_PREFIXES = (
    "get_",
    "list_",
    "inspect_",
    "analyze_",
    "check_",
    "find_",
    "search_",
    "measure",
    "lookup_",
    "capture_",
    "look",
    "render_viewport",
    "blend_file_info",
    "diagnose",
)
_NO_UNDO = {"undo", "redo", "create_checkpoint", "restore_checkpoint"}
_depth = 0


def history():
    return _HISTORY


def _summarize(params: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in list(params.items())[:12]:
        text = repr(value)
        out[key] = text if len(text) <= 120 else text[:117] + "..."
    return out


def _push_undo(command_name: str) -> None:
    if command_name in _NO_UNDO or command_name.startswith(_READ_ONLY_PREFIXES):
        return
    try:
        import bpy

        if bpy.context.window_manager.windows:
            bpy.ops.ed.undo_push(message=f"MCP: {command_name}")
    except Exception:  # noqa: BLE001 - undo is best effort (background mode, bad context)
        pass


_HANDLER_MODULES = (
    "analysis",
    "animation",
    "animation_advanced",
    "api_docs",
    "assets",
    "cameras",
    "collections",
    "compositing",
    "diagnostics",
    "geometry_nodes",
    "grease_pencil",
    "import_export",
    "library",
    "lighting",
    "materials",
    "meshes",
    "modeling",
    "modifiers",
    "objects",
    "physics",
    "render_config",
    "rendering",
    "rigging",
    "scene",
    "scene_builder",
    "screenshots",
    "scripting",
    "sculpting",
    "shading",
    "uv",
    "video_editing",
    "world",
)


def command(name: str):
    def decorator(func: Handler) -> Handler:
        _REGISTRY[name] = func
        return func

    return decorator


def dispatch(command_name: str, params: dict[str, Any]) -> dict[str, Any]:
    if not command_name:
        return {"success": False, "error_code": "INVALID_PARAMETER", "error": "Missing command"}
    if not _REGISTRY:
        # Recover after addon disable/enable without Blender restart (imports are cached).
        register()
    handler = _REGISTRY.get(command_name)
    if handler is None:
        return {
            "success": False,
            "error_code": "NOT_IMPLEMENTED",
            "error": f"Unknown command: {command_name}",
            "details": {"registered_commands": len(_REGISTRY)},
        }
    global _depth
    started = time.perf_counter()
    _depth += 1
    response = _run(handler, params)
    _depth -= 1
    _HISTORY.append(
        {
            "time": time.strftime("%H:%M:%S"),
            "command": command_name,
            "params": _summarize(params or {}),
            "success": bool(response.get("success")),
            "error": response.get("error"),
            "seconds": round(time.perf_counter() - started, 3),
            "nested": _depth > 0,
        }
    )
    if response.get("success") and _depth == 0:
        _push_undo(command_name)
    return response


def _run(handler: Handler, params: dict[str, Any]) -> dict[str, Any]:
    try:
        result = handler(params or {})
        if isinstance(result, dict) and "success" in result:
            return result
        return {"success": True, "result": result}
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("OBJECT_NOT_FOUND:"):
            return {
                "success": False,
                "error_code": "OBJECT_NOT_FOUND",
                "error": f"Object not found: {msg.split(':', 1)[1]}",
            }
        return {"success": False, "error_code": "INVALID_PARAMETER", "error": msg}
    except PermissionError as exc:
        return {"success": False, "error_code": "PERMISSION_DENIED", "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error_code": "OPERATION_FAILED", "error": str(exc)}


def register() -> None:
    """Import (or reload) handler modules so @command decorators refill `_REGISTRY`.

    Blender keeps modules in ``sys.modules`` across addon disable/enable. A plain
    import after ``unregister()`` clears the registry would otherwise leave zero
    commands registered because decorators do not run again.
    """
    pkg = __name__
    # Reload shared helpers before handlers so ``from .. import screenshots`` etc.
    # see the updated module instead of a stale cached copy.
    root = pkg.rsplit(".", 1)[0]
    for helper in ("screenshots",):
        full = f"{root}.{helper}"
        if full in sys.modules:
            importlib.reload(sys.modules[full])
    unsaved = importlib.import_module(f"{root}.unsaved")
    unsaved.register()
    for name in _HANDLER_MODULES:
        full = f"{pkg}.{name}"
        if full in sys.modules:
            importlib.reload(sys.modules[full])
        else:
            importlib.import_module(full)


def unregister() -> None:
    _REGISTRY.clear()
    unsaved = sys.modules.get(f"{__name__.rsplit('.', 1)[0]}.unsaved")
    if unsaved is not None:
        unsaved.unregister()
