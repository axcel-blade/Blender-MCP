"""N-panel UI: Blender MCP."""

from __future__ import annotations

import bpy
from bpy.types import Panel

from . import bridge_server


class VIEW3D_PT_blender_mcp(Panel):
    bl_label = "Blender MCP"
    bl_idname = "VIEW3D_PT_blender_mcp"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Blender MCP"

    def draw(self, context):
        layout = self.layout
        state = bridge_server.get_state()
        from .utils.prefs import get_preferences

        prefs = get_preferences()

        box = layout.box()
        box.label(text="Connection")
        status = "RUNNING" if bridge_server.is_server_alive() else "STOPPED"
        row = box.row()
        row.label(text=f"Status: {status}")
        if state.get("running") and not bridge_server.is_server_alive():
            box.label(text="Stale state — press Start to recover")
        if prefs:
            box.prop(prefs, "host")
            box.prop(prefs, "port")
            box.prop(prefs, "auto_start")
        row = box.row(align=True)
        row.operator("blendermcp.start_server", text="Start")
        row.operator("blendermcp.stop_server", text="Stop")
        box.operator("blendermcp.test_connection", text="Connection Test")

        box = layout.box()
        box.label(text="Configuration")
        if prefs:
            box.prop(prefs, "safe_execution_mode")
            box.prop(prefs, "script_permission")
            box.prop(prefs, "execution_timeout")
            box.prop(prefs, "allow_remote")
            box.label(text="Open Add-on Preferences for tool groups & API keys")

        box = layout.box()
        box.label(text="Monitoring")
        box.label(text=f"Clients: {state.get('clients', 0)}")
        box.label(text=f"Last request: {state.get('last_request') or '-'}")
        box.label(text=f"Current: {state.get('current_operation') or '-'}")
        box.label(text=f"Duration ms: {state.get('last_duration_ms') or 0:.1f}")
        box.label(text=f"Last error: {state.get('last_error') or '-'}")
        box.operator("blendermcp.clear_logs", text="Clear Logs")
        logs = state.get("logs") or []
        for line in logs[-8:]:
            box.label(text=line[:60])


classes = (VIEW3D_PT_blender_mcp,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
