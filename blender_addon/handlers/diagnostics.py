"""Diagnostics handlers."""

from __future__ import annotations

from typing import Any

from . import command


@command("diagnose_blender_connection")
def diagnose_blender_connection(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    from .. import ADDON_VERSION, bridge_server
    from ..utils.prefs import get_preferences
    from . import _REGISTRY

    prefs = get_preferences()

    state = bridge_server.get_state()
    return {
        "blender_version": bpy.app.version_string,
        "addon_version": ADDON_VERSION,
        "bridge": state,
        "script_permission": getattr(prefs, "script_permission", "trusted") if prefs else "trusted",
        "safe_execution_mode": getattr(prefs, "safe_execution_mode", True) if prefs else True,
        "capabilities": {
            "screenshots": True,
            "rendering": True,
            "scripting": getattr(prefs, "enable_scripting", True) if prefs else True,
            "polyhaven": getattr(prefs, "use_polyhaven", True) if prefs else True,
        },
        "api_available": True,
        "commands": sorted(_REGISTRY),
    }


@command("quit_blender")
def quit_blender(params: dict[str, Any]) -> dict[str, Any]:
    """Quit Blender shortly after replying, optionally saving the open file first."""
    import bpy

    save = bool(params.get("save", False))
    filepath = bpy.data.filepath
    if save and not filepath:
        raise ValueError("The file has never been saved; pass save=False or save it first")
    from ..unsaved import has_unsaved_changes

    if not save and has_unsaved_changes() and not params.get("discard_changes", False):
        raise ValueError("The file has unsaved changes; pass save=True or discard_changes=True")

    def _quit() -> None:
        if save:
            bpy.ops.wm.save_mainfile()
        bpy.ops.wm.quit_blender()

    # Defer so the bridge can send this reply before Blender exits.
    bpy.app.timers.register(_quit, first_interval=0.5)
    return {"quitting": True, "saved": save, "filepath": filepath}
