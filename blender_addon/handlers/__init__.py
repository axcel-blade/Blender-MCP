"""Command dispatch for Blender MCP handlers."""

from __future__ import annotations

from typing import Any, Callable

Handler = Callable[[dict[str, Any]], Any]
_REGISTRY: dict[str, Handler] = {}


def command(name: str):
    def decorator(func: Handler) -> Handler:
        _REGISTRY[name] = func
        return func

    return decorator


def dispatch(command_name: str, params: dict[str, Any]) -> dict[str, Any]:
    if not command_name:
        return {"success": False, "error_code": "INVALID_PARAMETER", "error": "Missing command"}
    handler = _REGISTRY.get(command_name)
    if handler is None:
        return {
            "success": False,
            "error_code": "NOT_IMPLEMENTED",
            "error": f"Unknown command: {command_name}",
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
    # Import handler modules for side-effect registration
    from . import (  # noqa: F401
        animation,
        assets,
        cameras,
        collections,
        diagnostics,
        geometry_nodes,
        import_export,
        lighting,
        materials,
        meshes,
        modifiers,
        objects,
        rendering,
        scene,
        screenshots,
        scripting,
    )


def unregister() -> None:
    _REGISTRY.clear()
