"""Command dispatch for Blender MCP handlers."""

from __future__ import annotations

import importlib
import sys
from typing import Any, Callable

Handler = Callable[[dict[str, Any]], Any]
_REGISTRY: dict[str, Handler] = {}

_HANDLER_MODULES = (
    "animation",
    "assets",
    "cameras",
    "collections",
    "diagnostics",
    "geometry_nodes",
    "import_export",
    "lighting",
    "materials",
    "meshes",
    "modifiers",
    "objects",
    "rendering",
    "scene",
    "screenshots",
    "scripting",
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
    for name in _HANDLER_MODULES:
        full = f"{pkg}.{name}"
        if full in sys.modules:
            importlib.reload(sys.modules[full])
        else:
            importlib.import_module(full)


def unregister() -> None:
    _REGISTRY.clear()
