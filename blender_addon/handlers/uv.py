"""UV mapping handlers."""

from __future__ import annotations

import math
from typing import Any

from ..utils.context import object_mode, require_mesh
from ..utils.objects import get_object
from . import command

_METHODS = ("smart", "unwrap", "cube", "cylinder", "sphere", "lightmap", "project_view")


@command("uv_unwrap")
def uv_unwrap(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    method = (params.get("method") or "smart").lower()
    if method not in _METHODS:
        raise ValueError(f"method must be one of {_METHODS}")
    margin = float(params.get("island_margin") or 0.02)
    if params.get("uv_map"):
        layer = obj.data.uv_layers.get(params["uv_map"]) or obj.data.uv_layers.new(
            name=params["uv_map"]
        )
        obj.data.uv_layers.active = layer
    elif not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
    with object_mode(obj, "EDIT") as override, bpy.context.temp_override(**override):
        bpy.ops.mesh.select_all(action="SELECT")
        if method == "smart":
            bpy.ops.uv.smart_project(
                angle_limit=math.radians(float(params.get("angle_limit") or 66.0)),
                island_margin=margin,
            )
        elif method == "unwrap":
            bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=margin)
        elif method == "cube":
            bpy.ops.uv.cube_project(cube_size=float(params.get("cube_size") or 1.0))
        elif method == "cylinder":
            bpy.ops.uv.cylinder_project()
        elif method == "sphere":
            bpy.ops.uv.sphere_project()
        elif method == "lightmap":
            bpy.ops.uv.lightmap_pack(PREF_MARGIN_DIV=max(margin, 0.01))
        elif method == "project_view":
            bpy.ops.uv.project_from_view(scale_to_bounds=True)
    return {"name": obj.name, "method": method, "uv_map": obj.data.uv_layers.active.name}


@command("mark_uv_seams")
def mark_uv_seams(params: dict[str, Any]):
    import bmesh

    obj = get_object(params["name"])
    require_mesh(obj)
    mode = (params.get("mode") or "sharp").lower()
    angle = math.radians(float(params.get("angle") or 30.0))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    count = 0
    indices = set(params.get("edge_indices") or [])
    for e in bm.edges:
        mark = False
        if mode == "sharp":
            mark = len(e.link_faces) == 2 and e.calc_face_angle(0.0) >= angle
        elif mode == "boundary":
            mark = e.is_boundary
        elif mode == "indices":
            mark = e.index in indices
        elif mode == "clear":
            e.seam = False
            continue
        if mark:
            e.seam = True
            count += 1
    bm.to_mesh(obj.data)
    bm.free()
    return {"name": obj.name, "mode": mode, "seams_marked": count}


@command("pack_uv_islands")
def pack_uv_islands(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    with object_mode(obj, "EDIT") as override, bpy.context.temp_override(**override):
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(
            margin=float(params.get("margin") or 0.02), rotate=bool(params.get("rotate", True))
        )
    return {"name": obj.name, "packed": True}


@command("get_uv_info")
def get_uv_info(params: dict[str, Any]):
    obj = get_object(params["name"])
    require_mesh(obj)
    mesh = obj.data
    info = {"name": obj.name, "uv_maps": [], "seams": sum(1 for e in mesh.edges if e.use_seam)}
    for layer in mesh.uv_layers:
        out_of_bounds = sum(1 for d in layer.data if not (0 <= d.uv.x <= 1 and 0 <= d.uv.y <= 1))
        zero_area = 0
        for poly in mesh.polygons:
            uvs = [layer.data[i].uv for i in poly.loop_indices]
            area = 0.0
            for i in range(len(uvs)):
                a, b = uvs[i], uvs[(i + 1) % len(uvs)]
                area += a.x * b.y - b.x * a.y
            if abs(area) < 1e-9:
                zero_area += 1
        info["uv_maps"].append(
            {
                "name": layer.name,
                "active": layer == mesh.uv_layers.active,
                "loops_outside_0_1": out_of_bounds,
                "zero_area_faces": zero_area,
            }
        )
    return info
