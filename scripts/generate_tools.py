"""One-shot generator for remaining MCP tool wrapper modules."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src" / "blender_mcp" / "tools"

TEMPLATE = '''"""{doc} MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:
{body}
'''


def tool(name: str, group: str, params: list[tuple], params_dict: str, doc: str) -> str:
    lines = []
    for pname, ptype, default in params:
        if default is Ellipsis:
            lines.append(f"        {pname}: {ptype},")
        else:
            lines.append(f"        {pname}: {ptype} = {default},")
    args = "\n".join(lines) if lines else "    "
    return f'''
    @mcp.tool(name="{name}")
    async def {name}(
{args}
    ) -> dict[str, Any]:
        """{doc}"""
        return await call_blender(ctx, "{name}", {{{params_dict}}}, group="{group}")
'''


def write(module: str, doc: str, tools: list) -> None:
    body = "".join(tool(*t) for t in tools)
    path = TOOLS / f"{module}.py"
    path.write_text(TEMPLATE.format(doc=doc, body=body), encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


write(
    "meshes",
    "Mesh modeling",
    [
        (
            "edit_mesh",
            "meshes",
            [
                ("name", "str", Ellipsis),
                ("operation", "str", Ellipsis),
                ("params", "dict[str, Any] | None", "None"),
            ],
            '"name": name, "operation": operation, "params": params or {}',
            "Run a structured mesh edit operation on an object.",
        ),
        (
            "extrude_mesh",
            "meshes",
            [("name", "str", Ellipsis), ("offset", "list[float] | None", "None")],
            '"name": name, "offset": offset',
            "Extrude selected mesh geometry (object-mode helper).",
        ),
        (
            "inset_faces",
            "meshes",
            [("name", "str", Ellipsis), ("thickness", "float", "0.1")],
            '"name": name, "thickness": thickness',
            "Inset faces on a mesh object.",
        ),
        (
            "bevel_mesh",
            "meshes",
            [("name", "str", Ellipsis), ("amount", "float", "0.1"), ("segments", "int", "1")],
            '"name": name, "amount": amount, "segments": segments',
            "Bevel mesh edges.",
        ),
        (
            "subdivide_mesh",
            "meshes",
            [("name", "str", Ellipsis), ("cuts", "int", "1")],
            '"name": name, "cuts": cuts',
            "Subdivide mesh faces.",
        ),
        (
            "merge_vertices",
            "meshes",
            [("name", "str", Ellipsis), ("distance", "float", "0.0001")],
            '"name": name, "distance": distance',
            "Merge vertices by distance.",
        ),
        (
            "delete_geometry",
            "meshes",
            [("name", "str", Ellipsis), ("mode", "str", '"VERT"')],
            '"name": name, "mode": mode',
            "Delete mesh geometry components.",
        ),
        (
            "fill_faces",
            "meshes",
            [("name", "str", Ellipsis)],
            '"name": name',
            "Fill selected boundary with faces where possible.",
        ),
        (
            "triangulate_mesh",
            "meshes",
            [("name", "str", Ellipsis)],
            '"name": name',
            "Triangulate a mesh.",
        ),
        (
            "remesh_mesh",
            "meshes",
            [("name", "str", Ellipsis), ("octree_depth", "int", "4"), ("mode", "str", '"SMOOTH"')],
            '"name": name, "octree_depth": octree_depth, "mode": mode',
            "Apply remesh via modifier and apply it.",
        ),
        (
            "decimate_mesh",
            "meshes",
            [("name", "str", Ellipsis), ("ratio", "float", "0.5")],
            '"name": name, "ratio": ratio',
            "Decimate a mesh.",
        ),
        (
            "smooth_mesh",
            "meshes",
            [("name", "str", Ellipsis), ("factor", "float", "0.5"), ("repeat", "int", "1")],
            '"name": name, "factor": factor, "repeat": repeat',
            "Smooth mesh vertices.",
        ),
        (
            "recalculate_normals",
            "meshes",
            [("name", "str", Ellipsis), ("inside", "bool", "False")],
            '"name": name, "inside": inside',
            "Recalculate mesh normals.",
        ),
        (
            "mesh_cleanup",
            "meshes",
            [("name", "str", Ellipsis)],
            '"name": name',
            "Run common mesh cleanup operations.",
        ),
    ],
)

write(
    "modifiers",
    "Modifier",
    [
        (
            "add_modifier",
            "modifiers",
            [
                ("name", "str", Ellipsis),
                ("modifier_type", "str", Ellipsis),
                ("modifier_name", "str | None", "None"),
                ("settings", "dict[str, Any] | None", "None"),
            ],
            '"name": name, "modifier_type": modifier_type, "modifier_name": modifier_name, "settings": settings or {}',
            "Add a modifier to an object.",
        ),
        (
            "remove_modifier",
            "modifiers",
            [("name", "str", Ellipsis), ("modifier_name", "str", Ellipsis)],
            '"name": name, "modifier_name": modifier_name',
            "Remove a modifier from an object.",
        ),
        (
            "modify_modifier",
            "modifiers",
            [
                ("name", "str", Ellipsis),
                ("modifier_name", "str", Ellipsis),
                ("settings", "dict[str, Any]", Ellipsis),
            ],
            '"name": name, "modifier_name": modifier_name, "settings": settings',
            "Update modifier settings.",
        ),
        (
            "apply_modifier",
            "modifiers",
            [("name", "str", Ellipsis), ("modifier_name", "str", Ellipsis)],
            '"name": name, "modifier_name": modifier_name',
            "Apply a modifier.",
        ),
        (
            "list_modifiers",
            "modifiers",
            [("name", "str", Ellipsis)],
            '"name": name',
            "List modifiers on an object with settings.",
        ),
    ],
)

write(
    "materials",
    "Material",
    [
        (
            "create_material",
            "materials",
            [
                ("name", "str | None", "None"),
                ("base_color", "list[float] | None", "None"),
                ("metallic", "float", "0.0"),
                ("roughness", "float", "0.5"),
            ],
            '"name": name, "base_color": base_color, "metallic": metallic, "roughness": roughness',
            "Create a Principled BSDF material.",
        ),
        (
            "assign_material",
            "materials",
            [
                ("object_name", "str", Ellipsis),
                ("material_name", "str", Ellipsis),
                ("slot", "int", "0"),
            ],
            '"object_name": object_name, "material_name": material_name, "slot": slot',
            "Assign a material to an object.",
        ),
        (
            "remove_material",
            "materials",
            [("object_name", "str", Ellipsis), ("slot", "int", "0")],
            '"object_name": object_name, "slot": slot',
            "Remove a material slot from an object.",
        ),
        (
            "modify_material",
            "materials",
            [("name", "str", Ellipsis), ("settings", "dict[str, Any]", Ellipsis)],
            '"name": name, "settings": settings',
            "Modify Principled BSDF inputs on a material.",
        ),
        (
            "get_material_info",
            "materials",
            [("name", "str", Ellipsis)],
            '"name": name',
            "Inspect a material and its nodes.",
        ),
        ("list_materials", "materials", [], "", "List all materials."),
        (
            "set_material_color",
            "materials",
            [("name", "str", Ellipsis), ("color", "list[float]", Ellipsis)],
            '"name": name, "color": color',
            "Set material base color.",
        ),
        (
            "set_material_properties",
            "materials",
            [("name", "str", Ellipsis), ("properties", "dict[str, Any]", Ellipsis)],
            '"name": name, "properties": properties',
            "Set common Principled BSDF properties.",
        ),
        (
            "create_basic_shader",
            "materials",
            [("name", "str | None", "None"), ("color", "list[float] | None", "None")],
            '"name": name, "color": color',
            "Create a basic Principled material.",
        ),
        (
            "create_emission_material",
            "materials",
            [
                ("name", "str | None", "None"),
                ("color", "list[float] | None", "None"),
                ("strength", "float", "5.0"),
            ],
            '"name": name, "color": color, "strength": strength',
            "Create an emission material.",
        ),
        (
            "create_metallic_material",
            "materials",
            [
                ("name", "str | None", "None"),
                ("color", "list[float] | None", "None"),
                ("roughness", "float", "0.2"),
            ],
            '"name": name, "color": color, "roughness": roughness',
            "Create a metallic material.",
        ),
        (
            "create_glass_material",
            "materials",
            [
                ("name", "str | None", "None"),
                ("ior", "float", "1.45"),
                ("roughness", "float", "0.0"),
            ],
            '"name": name, "ior": ior, "roughness": roughness',
            "Create a glass material.",
        ),
        (
            "create_transparent_material",
            "materials",
            [
                ("name", "str | None", "None"),
                ("alpha", "float", "0.3"),
                ("color", "list[float] | None", "None"),
            ],
            '"name": name, "alpha": alpha, "color": color',
            "Create a transparent material.",
        ),
        (
            "get_material_nodes",
            "materials",
            [("name", "str", Ellipsis)],
            '"name": name',
            "List nodes in a material node tree.",
        ),
        (
            "set_material_nodes",
            "materials",
            [("name", "str", Ellipsis), ("operations", "list[dict[str, Any]]", Ellipsis)],
            '"name": name, "operations": operations',
            "Apply structured node operations to a material.",
        ),
        (
            "assign_texture",
            "materials",
            [
                ("material_name", "str", Ellipsis),
                ("image_path", "str", Ellipsis),
                ("input_name", "str", '"Base Color"'),
            ],
            '"material_name": material_name, "image_path": image_path, "input_name": input_name',
            "Assign an image texture to a material input.",
        ),
    ],
)

write(
    "geometry_nodes",
    "Geometry Nodes",
    [
        (
            "create_geometry_nodes_modifier",
            "geometry_nodes",
            [("name", "str", Ellipsis), ("group_name", "str | None", "None")],
            '"name": name, "group_name": group_name',
            "Add a Geometry Nodes modifier.",
        ),
        (
            "create_node_group",
            "geometry_nodes",
            [("name", "str | None", "None")],
            '"name": name',
            "Create a geometry node group.",
        ),
        (
            "add_geometry_node",
            "geometry_nodes",
            [
                ("group_name", "str", Ellipsis),
                ("node_type", "str", Ellipsis),
                ("node_name", "str | None", "None"),
            ],
            '"group_name": group_name, "node_type": node_type, "node_name": node_name',
            "Add a node to a geometry node group.",
        ),
        (
            "connect_geometry_nodes",
            "geometry_nodes",
            [
                ("group_name", "str", Ellipsis),
                ("from_node", "str", Ellipsis),
                ("from_socket", "str", Ellipsis),
                ("to_node", "str", Ellipsis),
                ("to_socket", "str", Ellipsis),
            ],
            '"group_name": group_name, "from_node": from_node, "from_socket": from_socket, "to_node": to_node, "to_socket": to_socket',
            "Connect two geometry nodes.",
        ),
        (
            "set_geometry_node_input",
            "geometry_nodes",
            [
                ("group_name", "str", Ellipsis),
                ("node_name", "str", Ellipsis),
                ("input_name", "str", Ellipsis),
                ("value", "Any", Ellipsis),
            ],
            '"group_name": group_name, "node_name": node_name, "input_name": input_name, "value": value',
            "Set a geometry node input value.",
        ),
        (
            "inspect_node_group",
            "geometry_nodes",
            [("group_name", "str", Ellipsis)],
            '"group_name": group_name',
            "Inspect a node group structure.",
        ),
        (
            "list_geometry_node_types",
            "geometry_nodes",
            [],
            "",
            "List available geometry node type identifiers.",
        ),
        (
            "get_node_socket_info",
            "geometry_nodes",
            [("group_name", "str", Ellipsis), ("node_name", "str", Ellipsis)],
            '"group_name": group_name, "node_name": node_name',
            "Get socket schema for a node.",
        ),
    ],
)

write(
    "cameras",
    "Camera",
    [
        (
            "create_camera",
            "cameras",
            [
                ("name", "str | None", "None"),
                ("location", "list[float] | None", "None"),
                ("rotation", "list[float] | None", "None"),
                ("lens", "float", "50.0"),
                ("set_active", "bool", "True"),
            ],
            '"name": name, "location": location, "rotation": rotation, "lens": lens, "set_active": set_active',
            "Create a camera.",
        ),
        (
            "modify_camera",
            "cameras",
            [("name", "str", Ellipsis), ("settings", "dict[str, Any]", Ellipsis)],
            '"name": name, "settings": settings',
            "Modify camera settings.",
        ),
        (
            "set_active_camera",
            "cameras",
            [("name", "str", Ellipsis)],
            '"name": name',
            "Set the active scene camera.",
        ),
        (
            "focus_camera_on_object",
            "cameras",
            [("camera", "str", Ellipsis), ("object_name", "str", Ellipsis)],
            '"camera": camera, "object_name": object_name',
            "Point/focus a camera at an object.",
        ),
        (
            "frame_objects",
            "cameras",
            [("camera", "str | None", "None"), ("object_names", "list[str] | None", "None")],
            '"camera": camera, "object_names": object_names',
            "Frame objects in a camera view.",
        ),
        (
            "configure_camera_lens",
            "cameras",
            [
                ("name", "str", Ellipsis),
                ("lens", "float | None", "None"),
                ("type", "str | None", "None"),
                ("ortho_scale", "float | None", "None"),
            ],
            '"name": name, "lens": lens, "type": type, "ortho_scale": ortho_scale',
            "Configure camera lens settings.",
        ),
        (
            "configure_camera_depth_of_field",
            "cameras",
            [
                ("name", "str", Ellipsis),
                ("enabled", "bool", "True"),
                ("focus_object", "str | None", "None"),
                ("focus_distance", "float | None", "None"),
                ("fstop", "float", "2.8"),
            ],
            '"name": name, "enabled": enabled, "focus_object": focus_object, "focus_distance": focus_distance, "fstop": fstop',
            "Configure camera depth of field.",
        ),
        (
            "camera_view",
            "cameras",
            [("name", "str | None", "None")],
            '"name": name',
            "Return camera framing metadata for visual verification.",
        ),
    ],
)

write(
    "lighting",
    "Lighting",
    [
        (
            "create_light",
            "lighting",
            [
                ("light_type", "str", '"POINT"'),
                ("name", "str | None", "None"),
                ("location", "list[float] | None", "None"),
                ("energy", "float", "1000.0"),
                ("color", "list[float] | None", "None"),
            ],
            '"light_type": light_type, "name": name, "location": location, "energy": energy, "color": color',
            "Create a light.",
        ),
        (
            "modify_light",
            "lighting",
            [("name", "str", Ellipsis), ("settings", "dict[str, Any]", Ellipsis)],
            '"name": name, "settings": settings',
            "Modify light settings.",
        ),
        (
            "delete_light",
            "lighting",
            [("name", "str", Ellipsis), ("confirmed", "bool", "False")],
            '"name": name, "confirmed": confirmed',
            "Delete a light object.",
        ),
        (
            "get_light_info",
            "lighting",
            [("name", "str | None", "None")],
            '"name": name',
            "Get light information.",
        ),
        (
            "create_lighting_setup",
            "lighting",
            [("preset", "str", '"three_point"'), ("target", "str | None", "None")],
            '"preset": preset, "target": target',
            "Create a lighting preset (three_point, studio, product, outdoor, interior, cinematic).",
        ),
    ],
)

write(
    "rendering",
    "Rendering",
    [
        (
            "render_scene",
            "rendering",
            [
                ("engine", "str | None", "None"),
                ("samples", "int | None", "None"),
                ("resolution_percentage", "int", "50"),
                ("write_still", "bool", "True"),
                ("output_path", "str | None", "None"),
            ],
            '"engine": engine, "samples": samples, "resolution_percentage": resolution_percentage, "write_still": write_still, "output_path": output_path',
            "Render the current frame.",
        ),
        (
            "render_preview",
            "rendering",
            [("resolution_percentage", "int", "25"), ("samples", "int", "16")],
            '"resolution_percentage": resolution_percentage, "samples": samples, "preview": True',
            "Render a fast preview image.",
        ),
        (
            "render_final",
            "rendering",
            [("output_path", "str | None", "None"), ("samples", "int | None", "None")],
            '"output_path": output_path, "samples": samples, "final": True',
            "Render a higher-quality still.",
        ),
        (
            "render_animation",
            "rendering",
            [
                ("frame_start", "int | None", "None"),
                ("frame_end", "int | None", "None"),
                ("output_path", "str | None", "None"),
            ],
            '"frame_start": frame_start, "frame_end": frame_end, "output_path": output_path',
            "Render an animation range.",
        ),
        ("get_render_settings", "rendering", [], "", "Get render settings."),
        (
            "set_render_settings",
            "rendering",
            [("settings", "dict[str, Any]", Ellipsis)],
            '"settings": settings',
            "Update render settings with configured limits enforced.",
        ),
        (
            "set_output_path",
            "rendering",
            [("path", "str", Ellipsis)],
            '"path": path',
            "Set render output path.",
        ),
        ("get_render_result", "rendering", [], "", "Return the last render result path/metadata."),
    ],
)

write(
    "animation",
    "Animation",
    [
        (
            "create_keyframe",
            "animation",
            [
                ("name", "str", Ellipsis),
                ("data_path", "str", Ellipsis),
                ("frame", "int | None", "None"),
                ("index", "int", "-1"),
            ],
            '"name": name, "data_path": data_path, "frame": frame, "index": index',
            "Insert a keyframe on an object.",
        ),
        (
            "set_keyframe",
            "animation",
            [
                ("name", "str", Ellipsis),
                ("data_path", "str", Ellipsis),
                ("value", "Any", Ellipsis),
                ("frame", "int | None", "None"),
            ],
            '"name": name, "data_path": data_path, "value": value, "frame": frame',
            "Set a property value and keyframe it.",
        ),
        (
            "remove_keyframe",
            "animation",
            [
                ("name", "str", Ellipsis),
                ("data_path", "str", Ellipsis),
                ("frame", "int | None", "None"),
            ],
            '"name": name, "data_path": data_path, "frame": frame',
            "Remove a keyframe.",
        ),
        (
            "animate_location",
            "animation",
            [
                ("name", "str", Ellipsis),
                ("location", "list[float]", Ellipsis),
                ("frame", "int", Ellipsis),
            ],
            '"name": name, "location": location, "frame": frame',
            "Keyframe object location.",
        ),
        (
            "animate_rotation",
            "animation",
            [
                ("name", "str", Ellipsis),
                ("rotation", "list[float]", Ellipsis),
                ("frame", "int", Ellipsis),
            ],
            '"name": name, "rotation": rotation, "frame": frame',
            "Keyframe object rotation.",
        ),
        (
            "animate_scale",
            "animation",
            [
                ("name", "str", Ellipsis),
                ("scale", "list[float]", Ellipsis),
                ("frame", "int", Ellipsis),
            ],
            '"name": name, "scale": scale, "frame": frame',
            "Keyframe object scale.",
        ),
        (
            "set_animation_range",
            "animation",
            [("frame_start", "int", Ellipsis), ("frame_end", "int", Ellipsis)],
            '"frame_start": frame_start, "frame_end": frame_end',
            "Set scene animation range.",
        ),
        (
            "set_current_frame",
            "animation",
            [("frame", "int", Ellipsis)],
            '"frame": frame',
            "Set the current frame.",
        ),
        (
            "inspect_animation",
            "animation",
            [("name", "str | None", "None")],
            '"name": name',
            "Inspect animation data.",
        ),
        (
            "create_animation_preview",
            "animation",
            [
                ("frame_start", "int | None", "None"),
                ("frame_end", "int | None", "None"),
                ("step", "int", "5"),
            ],
            '"frame_start": frame_start, "frame_end": frame_end, "step": step',
            "Capture frames for an animation preview strip.",
        ),
    ],
)

write(
    "collections",
    "Collection",
    [
        (
            "create_collection",
            "collections",
            [("name", "str", Ellipsis), ("parent", "str | None", "None")],
            '"name": name, "parent": parent',
            "Create a collection.",
        ),
        (
            "delete_collection",
            "collections",
            [("name", "str", Ellipsis), ("confirmed", "bool", "False")],
            '"name": name, "confirmed": confirmed',
            "Delete a collection.",
        ),
        (
            "rename_collection",
            "collections",
            [("name", "str", Ellipsis), ("new_name", "str", Ellipsis)],
            '"name": name, "new_name": new_name',
            "Rename a collection.",
        ),
        (
            "move_object_to_collection",
            "collections",
            [
                ("object_name", "str", Ellipsis),
                ("collection", "str", Ellipsis),
                ("exclusive", "bool", "True"),
            ],
            '"object_name": object_name, "collection": collection, "exclusive": exclusive',
            "Move an object into a collection.",
        ),
        (
            "get_collection_info",
            "collections",
            [("name", "str", Ellipsis)],
            '"name": name',
            "Get collection details.",
        ),
        (
            "organize_scene",
            "collections",
            [("structure", "dict[str, list[str]] | None", "None")],
            '"structure": structure',
            "Organize objects into logical collections.",
        ),
        (
            "create_hierarchy",
            "collections",
            [("names", "list[str]", Ellipsis)],
            '"names": names',
            "Create nested collections by path names.",
        ),
    ],
)

write(
    "import_export",
    "Import/export",
    [
        (
            "import_asset",
            "import_export",
            [("path", "str", Ellipsis), ("collection", "str | None", "None")],
            '"path": path, "collection": collection',
            "Import a 3D asset (FBX/OBJ/STL/GLTF/GLB/USD/BLEND).",
        ),
        (
            "export_asset",
            "import_export",
            [
                ("path", "str", Ellipsis),
                ("objects", "list[str] | None", "None"),
                ("overwrite", "bool", "False"),
            ],
            '"path": path, "objects": objects, "overwrite": overwrite',
            "Export selected or named objects.",
        ),
        (
            "export_selected_objects",
            "import_export",
            [("path", "str", Ellipsis), ("overwrite", "bool", "False")],
            '"path": path, "overwrite": overwrite',
            "Export currently selected objects.",
        ),
        (
            "export_scene",
            "import_export",
            [("path", "str", Ellipsis), ("overwrite", "bool", "False")],
            '"path": path, "overwrite": overwrite',
            "Export the full scene.",
        ),
        (
            "save_blend_file",
            "import_export",
            [("path", "str | None", "None"), ("overwrite", "bool", "True")],
            '"path": path, "overwrite": overwrite',
            "Save the current .blend file.",
        ),
        (
            "save_as",
            "import_export",
            [("path", "str", Ellipsis), ("overwrite", "bool", "False")],
            '"path": path, "overwrite": overwrite',
            "Save the blend file to a new path.",
        ),
        (
            "open_blend_file",
            "import_export",
            [("path", "str", Ellipsis)],
            '"path": path',
            "Open a .blend file.",
        ),
        ("get_project_path", "import_export", [], "", "Get the current blend file path."),
    ],
)

write(
    "screenshots",
    "Screenshot / visual feedback",
    [
        (
            "get_viewport_screenshot",
            "screenshots",
            [("max_size", "int | None", "None"), ("shading", "str | None", "None")],
            '"max_size": max_size, "shading": shading',
            "Capture the 3D viewport as an image for visual verification.",
        ),
        (
            "capture_viewport",
            "screenshots",
            [
                ("max_size", "int | None", "None"),
                ("view", "str | None", "None"),
                ("shading", "str | None", "None"),
            ],
            '"max_size": max_size, "view": view, "shading": shading',
            "Capture the viewport with optional view/shading overrides.",
        ),
        (
            "capture_camera_view",
            "screenshots",
            [("camera", "str | None", "None"), ("max_size", "int | None", "None")],
            '"camera": camera, "max_size": max_size',
            "Capture from the active or named camera.",
        ),
        (
            "capture_scene_preview",
            "screenshots",
            [("max_size", "int | None", "None")],
            '"max_size": max_size',
            "Capture a scene preview image.",
        ),
        (
            "capture_multiple_angles",
            "screenshots",
            [("angles", "list[str] | None", "None"), ("max_size", "int | None", "None")],
            '"angles": angles, "max_size": max_size',
            "Capture multiple orthographic/perspective angles.",
        ),
        (
            "capture_wireframe",
            "screenshots",
            [("max_size", "int | None", "None")],
            '"max_size": max_size, "shading": "WIREFRAME"',
            "Capture a wireframe viewport image.",
        ),
        (
            "capture_material_preview",
            "screenshots",
            [("max_size", "int | None", "None")],
            '"max_size": max_size, "shading": "MATERIAL"',
            "Capture a material preview viewport image.",
        ),
        (
            "capture_render",
            "screenshots",
            [("max_size", "int | None", "None")],
            '"max_size": max_size',
            "Capture or return the latest render preview.",
        ),
        (
            "inspect_render",
            "screenshots",
            [],
            "",
            "Return metadata about the latest captured/rendered image.",
        ),
    ],
)

write(
    "scripting",
    "Script execution",
    [
        (
            "execute_blender_code",
            "scripting",
            [
                ("code", "str", Ellipsis),
                ("confirmed", "bool", "False"),
                ("preview_only", "bool", "False"),
                ("timeout", "float | None", "None"),
            ],
            '"code": code, "confirmed": confirmed, "preview_only": preview_only, "timeout": timeout',
            "Execute Python code inside Blender when script permissions allow it.",
        ),
    ],
)

write(
    "assets",
    "Asset provider",
    [
        (
            "search_assets",
            "assets",
            [
                ("source", "str", Ellipsis),
                ("query", "str", Ellipsis),
                ("asset_type", "str | None", "None"),
                ("limit", "int", "10"),
            ],
            '"source": source, "query": query, "asset_type": asset_type, "limit": limit',
            "Search external asset providers (polyhaven, sketchfab, polypizza).",
        ),
        (
            "import_external_asset",
            "assets",
            [
                ("source", "str", Ellipsis),
                ("asset_id", "str", Ellipsis),
                ("asset_type", "str | None", "None"),
                ("resolution", "str", '"1k"'),
            ],
            '"source": source, "asset_id": asset_id, "asset_type": asset_type, "resolution": resolution',
            "Download and import an asset from a configured provider.",
        ),
        (
            "list_asset_providers",
            "assets",
            [],
            "",
            "List configured asset providers and credential status (no secrets).",
        ),
    ],
)

print("done")
