"""Mesh modeling handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import active_select, get_object
from . import command


def _edit(obj):
    import bpy

    active_select(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")


def _object_mode():
    import bpy

    bpy.ops.object.mode_set(mode="OBJECT")


@command("edit_mesh")
def edit_mesh(params: dict[str, Any]):
    op = params["operation"]
    mapping = {
        "extrude": extrude_mesh,
        "inset": inset_faces,
        "bevel": bevel_mesh,
        "subdivide": subdivide_mesh,
        "merge": merge_vertices,
        "triangulate": triangulate_mesh,
        "smooth": smooth_mesh,
        "normals": recalculate_normals,
        "cleanup": mesh_cleanup,
    }
    handler = mapping.get(op)
    if handler is None:
        raise ValueError(f"Unsupported mesh operation: {op}")
    merged = dict(params.get("params") or {})
    merged["name"] = params["name"]
    return handler(merged)


@command("extrude_mesh")
def extrude_mesh(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value": tuple(params.get("offset") or [0, 0, 0.2])}
    )
    _object_mode()
    return {"name": obj.name, "operation": "extrude"}


@command("inset_faces")
def inset_faces(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.inset(thickness=float(params.get("thickness") or 0.1))
    _object_mode()
    return {"name": obj.name, "operation": "inset"}


@command("bevel_mesh")
def bevel_mesh(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.bevel(
        offset=float(params.get("amount") or 0.1),
        segments=int(params.get("segments") or 1),
    )
    _object_mode()
    return {"name": obj.name, "operation": "bevel"}


@command("subdivide_mesh")
def subdivide_mesh(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.subdivide(number_cuts=int(params.get("cuts") or 1))
    _object_mode()
    return {"name": obj.name, "operation": "subdivide"}


@command("merge_vertices")
def merge_vertices(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.remove_doubles(threshold=float(params.get("distance") or 0.0001))
    _object_mode()
    return {"name": obj.name, "operation": "merge"}


@command("delete_geometry")
def delete_geometry(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    mode = params.get("mode") or "VERT"
    type_map = {"VERT": "VERT", "EDGE": "EDGE", "FACE": "FACE", "ONLY_FACE": "ONLY_FACE"}
    bpy.ops.mesh.delete(type=type_map.get(mode, "VERT"))
    _object_mode()
    return {"name": obj.name, "operation": "delete", "mode": mode}


@command("fill_faces")
def fill_faces(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.fill()
    _object_mode()
    return {"name": obj.name, "operation": "fill"}


@command("triangulate_mesh")
def triangulate_mesh(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.quads_convert_to_tris()
    _object_mode()
    return {"name": obj.name, "operation": "triangulate"}


@command("remesh_mesh")
def remesh_mesh(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    mod = obj.modifiers.new("Remesh", "REMESH")
    mod.mode = params.get("mode") or "SMOOTH"
    mod.octree_depth = int(params.get("octree_depth") or 4)
    active_select(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return {"name": obj.name, "operation": "remesh"}


@command("decimate_mesh")
def decimate_mesh(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    mod = obj.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = float(params.get("ratio") or 0.5)
    active_select(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return {"name": obj.name, "operation": "decimate"}


@command("smooth_mesh")
def smooth_mesh(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.vertices_smooth(
        factor=float(params.get("factor") or 0.5),
        repeat=int(params.get("repeat") or 1),
    )
    _object_mode()
    return {"name": obj.name, "operation": "smooth"}


@command("recalculate_normals")
def recalculate_normals(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    if params.get("inside"):
        bpy.ops.mesh.normals_make_consistent(inside=True)
    else:
        bpy.ops.mesh.normals_make_consistent(inside=False)
    _object_mode()
    return {"name": obj.name, "operation": "recalculate_normals"}


@command("mesh_cleanup")
def mesh_cleanup(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    _edit(obj)
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.dissolve_degenerate()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    _object_mode()
    return {"name": obj.name, "operation": "cleanup"}
