"""Addon preferences."""

from __future__ import annotations

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import AddonPreferences


class BLENDERMCP_AddonPreferences(AddonPreferences):
    # Must match the top-level addon package folder name.
    bl_idname = __package__.split(".")[0] if __package__ else "blender_addon"

    host: StringProperty(name="Host", default="127.0.0.1")
    port: IntProperty(name="Port", default=9877, min=1, max=65535)
    bind_address: StringProperty(name="Bind Address", default="127.0.0.1")
    auth_token: StringProperty(name="Auth Token", default="", subtype="PASSWORD")
    auto_start: BoolProperty(name="Auto-start server", default=True)
    allow_remote: BoolProperty(
        name="Allow remote connections",
        default=False,
        description="Bind beyond localhost. No encryption — trusted networks only.",
    )

    safe_execution_mode: BoolProperty(name="Safe execution mode", default=True)
    script_permission: EnumProperty(
        name="Script permission",
        items=(
            ("restricted", "Restricted", "No arbitrary Python"),
            ("confirmation", "Confirmation", "Require confirmed=true"),
            ("trusted", "Trusted", "Allow execute_blender_code"),
        ),
        default="trusted",
    )
    execution_timeout: FloatProperty(name="Execution timeout", default=60.0, min=1.0)
    allowed_directories: StringProperty(
        name="Allowed directories",
        default="",
        description="Semicolon-separated allow-list for file paths",
    )

    enable_scene: BoolProperty(name="Scene tools", default=True)
    enable_objects: BoolProperty(name="Object tools", default=True)
    enable_meshes: BoolProperty(name="Mesh tools", default=True)
    enable_modifiers: BoolProperty(name="Modifier tools", default=True)
    enable_materials: BoolProperty(name="Material tools", default=True)
    enable_geometry_nodes: BoolProperty(name="Geometry Nodes tools", default=True)
    enable_cameras: BoolProperty(name="Camera tools", default=True)
    enable_lighting: BoolProperty(name="Lighting tools", default=True)
    enable_rendering: BoolProperty(name="Rendering tools", default=True)
    enable_animation: BoolProperty(name="Animation tools", default=True)
    enable_assets: BoolProperty(name="Asset tools", default=True)
    enable_import_export: BoolProperty(name="Import/Export tools", default=True)
    enable_collections: BoolProperty(name="Collection tools", default=True)
    enable_screenshots: BoolProperty(name="Screenshot tools", default=True)
    enable_scripting: BoolProperty(name="Scripting tools", default=True)

    render_max_samples: IntProperty(name="Max samples", default=128, min=1)
    render_max_resolution: IntProperty(name="Max resolution", default=1920, min=64)

    use_polyhaven: BoolProperty(name="Poly Haven", default=True)
    use_sketchfab: BoolProperty(name="Sketchfab", default=False)
    use_polypizza: BoolProperty(name="Poly Pizza", default=False)
    sketchfab_api_key: StringProperty(name="Sketchfab API Key", default="", subtype="PASSWORD")
    polypizza_api_key: StringProperty(name="Poly Pizza API Key", default="", subtype="PASSWORD")
    meshy_api_key: StringProperty(name="Meshy API Key", default="", subtype="PASSWORD")
    tripo_api_key: StringProperty(name="Tripo API Key", default="", subtype="PASSWORD")

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "host")
        col.prop(self, "port")
        col.prop(self, "bind_address")
        col.prop(self, "auth_token")
        col.prop(self, "auto_start")
        col.prop(self, "allow_remote")
        col.separator()
        col.prop(self, "safe_execution_mode")
        col.prop(self, "script_permission")
        col.prop(self, "execution_timeout")
        col.prop(self, "allowed_directories")
        col.separator()
        col.label(text="Tool groups")
        grid = col.grid_flow(columns=2, even_columns=True)
        for prop in (
            "enable_scene",
            "enable_objects",
            "enable_meshes",
            "enable_modifiers",
            "enable_materials",
            "enable_geometry_nodes",
            "enable_cameras",
            "enable_lighting",
            "enable_rendering",
            "enable_animation",
            "enable_assets",
            "enable_import_export",
            "enable_collections",
            "enable_screenshots",
            "enable_scripting",
        ):
            grid.prop(self, prop)
        col.separator()
        col.label(text="Asset providers")
        col.prop(self, "use_polyhaven")
        col.prop(self, "use_sketchfab")
        col.prop(self, "sketchfab_api_key")
        col.prop(self, "use_polypizza")
        col.prop(self, "polypizza_api_key")


classes = (BLENDERMCP_AddonPreferences,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
