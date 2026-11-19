"""Resolve addon preferences regardless of install folder name."""

from __future__ import annotations


def get_preferences():
    import bpy

    # blender_addon.utils.prefs -> blender_addon
    # blender_mcp_addon.utils.prefs -> blender_mcp_addon
    pkg = __package__.split(".")[0] if __package__ else "blender_addon"
    addon = bpy.context.preferences.addons.get(pkg)
    return addon.preferences if addon else None
