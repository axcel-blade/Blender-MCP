"""Blender MCP addon — TCP bridge for AI assistants."""

bl_info = {
    "name": "Blender MCP",
    "author": "AXCEL BLADE",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > AI / MCP",
    "description": "Connect Blender to MCP-compatible AI clients over a local bridge",
    "category": "Interface",
    "doc_url": "https://github.com/axcel-blade/Blender-MCP",
}

ADDON_VERSION = "0.1.0"

_modules = (
    "preferences",
    "execution_queue",
    "bridge_server",
    "handlers",
    "operators",
    "panel",
    "screenshots",
)


def register() -> None:
    import importlib

    pkg = __name__
    for name in _modules:
        module = importlib.import_module(f".{name}", pkg)
        if hasattr(module, "register"):
            module.register()

    prefs = _prefs()
    if prefs is not None and getattr(prefs, "auto_start", False):
        from . import bridge_server

        bridge_server.start_server()


def unregister() -> None:
    import importlib

    from . import bridge_server

    bridge_server.stop_server()

    pkg = __name__
    for name in reversed(_modules):
        module = importlib.import_module(f".{name}", pkg)
        if hasattr(module, "unregister"):
            module.unregister()


def _prefs():
    from .utils.prefs import get_preferences

    return get_preferences()
