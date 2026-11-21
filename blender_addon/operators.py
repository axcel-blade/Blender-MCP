"""Blender operators for the MCP panel."""

from __future__ import annotations

import bpy
from bpy.types import Operator

from . import bridge_server


class BLENDERMCP_OT_start_server(Operator):
    bl_idname = "blendermcp.start_server"
    bl_label = "Start MCP Server"
    bl_description = "Start the local Blender MCP bridge server"

    def execute(self, context):
        try:
            bridge_server.start_server()
            self.report({"INFO"}, "Blender MCP bridge started")
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class BLENDERMCP_OT_stop_server(Operator):
    bl_idname = "blendermcp.stop_server"
    bl_label = "Stop MCP Server"

    def execute(self, context):
        bridge_server.stop_server()
        self.report({"INFO"}, "Blender MCP bridge stopped")
        return {"FINISHED"}


class BLENDERMCP_OT_test_connection(Operator):
    bl_idname = "blendermcp.test_connection"
    bl_label = "Test Connection"

    def execute(self, context):
        state = bridge_server.get_state()
        probe = bridge_server.probe_listen()
        if probe.get("ok"):
            self.report(
                {"INFO"},
                f"Listening on {probe.get('host')}:{probe.get('port')} — "
                f"clients={state.get('clients')}",
            )
            return {"FINISHED"}

        if bridge_server.is_server_alive():
            self.report(
                {"WARNING"},
                f"Bridge marked running but TCP probe failed: {probe.get('error') or 'unknown'}",
            )
        else:
            self.report({"WARNING"}, "Bridge server is not running")
        return {"FINISHED"}


class BLENDERMCP_OT_clear_logs(Operator):
    bl_idname = "blendermcp.clear_logs"
    bl_label = "Clear Logs"

    def execute(self, context):
        bridge_server.get_state().get("logs", []).clear()
        bridge_server.log("Logs cleared")
        return {"FINISHED"}


classes = (
    BLENDERMCP_OT_start_server,
    BLENDERMCP_OT_stop_server,
    BLENDERMCP_OT_test_connection,
    BLENDERMCP_OT_clear_logs,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
