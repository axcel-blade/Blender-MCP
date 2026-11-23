"""Sculpting handlers: modes, brushes, procedural brush-style deformation, masks, remeshing."""

from __future__ import annotations

import contextlib
import math
from typing import Any

from ..utils.context import object_mode, require_mesh, require_version
from ..utils.objects import get_object
from . import command

# Brush display names shared by the legacy brush datablocks and 4.3+ essentials assets.
_BRUSHES = {
    "draw": "Draw",
    "clay": "Clay",
    "clay_strips": "Clay Strips",
    "inflate": "Inflate/Deflate",
    "smooth": "Smooth",
    "grab": "Grab",
    "crease": "Crease",
    "flatten": "Flatten/Contrast",
    "scrape": "Scrape/Fill",
    "pinch": "Pinch/Magnify",
    "snake_hook": "Snake Hook",
    "layer": "Layer",
    "blob": "Blob",
    "mask": "Mask",
}

DEFORM_OPS = (
    "draw",
    "clay",
    "inflate",
    "deflate",
    "smooth",
    "grab",
    "crease",
    "flatten",
    "scrape",
    "pinch",
    "snake_hook",
    "noise",
)


@command("set_sculpt_mode")
def set_sculpt_mode(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    enable = params.get("enable", True)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="SCULPT" if enable else "OBJECT")
    return {"name": obj.name, "mode": obj.mode}


@command("set_sculpt_brush")
def set_sculpt_brush(params: dict[str, Any]):
    import bpy

    key = (params.get("brush") or "draw").lower()
    display = _BRUSHES.get(key)
    if display is None:
        raise ValueError(f"Unknown brush {key!r}; valid: {sorted(_BRUSHES)}")
    sculpt = bpy.context.scene.tool_settings.sculpt
    activated = False
    if bpy.app.version >= (4, 3, 0):
        try:
            bpy.ops.brush.asset_activate(
                asset_library_type="ESSENTIALS",
                relative_asset_identifier=f"brushes/essentials_brushes-mesh_sculpt.blend/Brush/{display}",
            )
            activated = True
        except Exception:  # noqa: BLE001
            activated = False
    if not activated:
        brush = bpy.data.brushes.get(display)
        if brush is None:
            raise ValueError(f"Brush {display!r} not available in this Blender")
        sculpt.brush = brush
    brush = sculpt.brush
    if brush is not None:
        if params.get("strength") is not None:
            brush.strength = float(params["strength"])
        if params.get("radius_px") is not None:
            bpy.context.scene.tool_settings.unified_paint_settings.size = int(params["radius_px"])
            brush.size = int(params["radius_px"])
        if params.get("direction") in {"ADD", "SUBTRACT"} and hasattr(brush, "direction"):
            with contextlib.suppress(TypeError):
                brush.direction = params["direction"]
    return {"brush": brush.name if brush else display, "strength": getattr(brush, "strength", None)}


def _falloff(dist: float, radius: float, kind: str) -> float:
    if dist >= radius:
        return 0.0
    t = dist / radius
    if kind == "linear":
        return 1.0 - t
    if kind == "sharp":
        return (1.0 - t) ** 3
    if kind == "constant":
        return 1.0
    return 0.5 * (1.0 + math.cos(math.pi * t))  # smooth


@command("sculpt_deform")
def sculpt_deform(params: dict[str, Any]):
    """Brush-style deformation applied directly to vertices (works headless, deterministic)."""
    import bmesh
    import mathutils

    obj = get_object(params["name"])
    require_mesh(obj)
    op = (params.get("operation") or "draw").lower()
    if op not in DEFORM_OPS:
        raise ValueError(f"Unknown operation {op!r}; valid: {list(DEFORM_OPS)}")
    radius = float(params.get("radius") or 0.5)
    strength = float(params.get("strength") if params.get("strength") is not None else 0.5)
    falloff = params.get("falloff") or "smooth"
    iterations = max(1, min(int(params.get("iterations") or 1), 50))
    inv = obj.matrix_world.inverted()
    center = inv @ mathutils.Vector(params.get("center") or obj.location)
    direction = mathutils.Vector(params.get("direction") or (0, 0, 1))
    direction = (inv.to_3x3() @ direction).normalized() if direction.length else direction
    mask = _read_mask(obj.data)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    touched = 0
    for _ in range(iterations):
        affected = []
        for v in bm.verts:
            w = _falloff((v.co - center).length, radius, falloff)
            if mask is not None:
                w *= 1.0 - mask[v.index]
            if w > 0:
                affected.append((v, w * strength))
        if not affected:
            break
        avg_n = sum((v.normal for v, _ in affected), mathutils.Vector()).normalized()
        avg_c = sum((v.co for v, _ in affected), mathutils.Vector()) / len(affected)
        new_pos = {}
        for v, w in affected:
            if op in {"draw", "clay", "blob"}:
                new_pos[v] = v.co + v.normal * w * radius * 0.2
            elif op == "inflate":
                new_pos[v] = v.co + v.normal * w * radius * 0.1
            elif op == "deflate":
                new_pos[v] = v.co - v.normal * w * radius * 0.1
            elif op in {"grab", "snake_hook"}:
                new_pos[v] = v.co + direction * w * (radius if op == "snake_hook" else radius * 0.5)
            elif op == "smooth":
                if v.link_edges:
                    nb = sum((e.other_vert(v).co for e in v.link_edges), mathutils.Vector())
                    nb /= len(v.link_edges)
                    new_pos[v] = v.co.lerp(nb, min(w, 1.0))
            elif op in {"flatten", "scrape"}:
                offset = (v.co - avg_c).dot(avg_n)
                if op == "scrape" and offset < 0:
                    continue
                new_pos[v] = v.co - avg_n * offset * min(w, 1.0)
            elif op == "pinch":
                new_pos[v] = v.co.lerp(center, min(w * 0.3, 1.0))
            elif op == "crease":
                new_pos[v] = v.co.lerp(center, min(w * 0.2, 1.0)) - v.normal * w * radius * 0.1
            elif op == "noise":
                n = mathutils.noise.noise(v.co * (4.0 / radius))
                new_pos[v] = v.co + v.normal * n * w * radius * 0.2
        for v, co in new_pos.items():
            v.co = co
        touched = max(touched, len(new_pos))
        bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {
        "name": obj.name,
        "operation": op,
        "affected_vertices": touched,
        "iterations": iterations,
    }


def _mask_attr(mesh, create: bool):
    attrs = mesh.attributes
    attr = attrs.get(".sculpt_mask")
    if attr is None and create:
        attr = attrs.new(".sculpt_mask", "FLOAT", "POINT")
    return attr


def _read_mask(mesh):
    attr = _mask_attr(mesh, create=False)
    if attr is None:
        return None
    return [d.value for d in attr.data]


@command("sculpt_mask")
def sculpt_mask(params: dict[str, Any]):
    import mathutils

    obj = get_object(params["name"])
    require_mesh(obj)
    action = (params.get("action") or "clear").lower()
    mesh = obj.data
    attr = _mask_attr(mesh, create=action != "clear")
    if action == "clear":
        if attr is not None:
            mesh.attributes.remove(attr)
        return {"name": obj.name, "masked_vertices": 0}
    values = [d.value for d in attr.data]
    if action == "fill":
        values = [float(params.get("value", 1.0))] * len(values)
    elif action == "invert":
        values = [1.0 - v for v in values]
    elif action == "sphere":
        center = obj.matrix_world.inverted() @ mathutils.Vector(params.get("center") or (0, 0, 0))
        radius = float(params.get("radius") or 0.5)
        for i, v in enumerate(mesh.vertices):
            if (v.co - center).length <= radius:
                values[i] = float(params.get("value", 1.0))
    elif action == "vertex_group":
        group = obj.vertex_groups.get(params.get("vertex_group") or "")
        if group is None:
            raise ValueError("vertex_group not found")
        for i, v in enumerate(mesh.vertices):
            for g in v.groups:
                if g.group == group.index:
                    values[i] = g.weight
    elif action == "above_z" or action == "below_z":
        z = float(params.get("value", 0.0))
        for i, v in enumerate(mesh.vertices):
            wz = (obj.matrix_world @ v.co).z
            values[i] = 1.0 if (wz > z if action == "above_z" else wz < z) else 0.0
    else:
        raise ValueError(
            "action must be clear, fill, invert, sphere, vertex_group, above_z, below_z"
        )
    for d, v in zip(attr.data, values, strict=False):
        d.value = max(0.0, min(1.0, v))
    mesh.update()
    return {"name": obj.name, "masked_vertices": sum(1 for v in values if v > 0.5)}


@command("sculpt_face_sets")
def sculpt_face_sets(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    mode = (params.get("mode") or "LOOSE_PARTS").upper()
    with object_mode(obj, "SCULPT") as override, bpy.context.temp_override(**override):
        bpy.ops.sculpt.face_sets_init(mode=mode)
    attr = obj.data.attributes.get(".sculpt_face_set")
    count = len({d.value for d in attr.data}) if attr else 0
    return {"name": obj.name, "mode": mode, "face_sets": count}


@command("set_dynamic_topology")
def set_dynamic_topology(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    enable = bool(params.get("enable", True))
    bpy.context.view_layer.objects.active = obj
    if obj.mode != "SCULPT":
        bpy.ops.object.mode_set(mode="SCULPT")
    if bool(obj.use_dynamic_topology_sculpting) != enable:
        bpy.ops.sculpt.dynamic_topology_toggle()
    sculpt = bpy.context.scene.tool_settings.sculpt
    if params.get("detail_size") is not None:
        sculpt.detail_size = float(params["detail_size"])
    if params.get("detail_type"):
        sculpt.detail_type_method = params["detail_type"].upper()
    return {"name": obj.name, "dyntopo": obj.use_dynamic_topology_sculpting}


@command("voxel_remesh")
def voxel_remesh(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    before = len(obj.data.polygons)
    obj.data.remesh_voxel_size = float(params.get("voxel_size") or 0.05)
    obj.data.remesh_voxel_adaptivity = float(params.get("adaptivity") or 0.0)
    if hasattr(obj.data, "use_remesh_preserve_volume"):
        obj.data.use_remesh_preserve_volume = bool(params.get("preserve_volume", True))
    with object_mode(obj) as override, bpy.context.temp_override(**override):
        bpy.ops.object.voxel_remesh()
    return {"name": obj.name, "polygons_before": before, "polygons_after": len(obj.data.polygons)}


@command("add_multires")
def add_multires(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    mod = next((m for m in obj.modifiers if m.type == "MULTIRES"), None)
    if mod is None:
        mod = obj.modifiers.new("Multires", "MULTIRES")
    levels = max(0, min(int(params.get("levels") or 2), 6))
    with object_mode(obj) as override, bpy.context.temp_override(**override):
        for _ in range(levels):
            bpy.ops.object.multires_subdivide(modifier=mod.name, mode="CATMULL_CLARK")
    mod.sculpt_levels = mod.total_levels
    mod.levels = min(mod.total_levels, int(params.get("viewport_levels") or mod.total_levels))
    return {"name": obj.name, "modifier": mod.name, "total_levels": mod.total_levels}


@command("sculpt_stroke")
def sculpt_stroke(params: dict[str, Any]):
    """Real sculpt brush stroke through the UI operator. Needs a visible 3D viewport."""
    import bpy
    from bpy_extras import view3d_utils

    require_version((3, 6), "sculpt_stroke")
    obj = get_object(params["name"])
    require_mesh(obj)
    points = params.get("points") or []
    if len(points) < 2:
        raise ValueError("points needs at least two world-space positions")
    with object_mode(obj, "SCULPT") as override:
        if not override:
            raise ValueError("sculpt_stroke needs a 3D viewport; use sculpt_deform when headless")
        region, rv3d = override["region"], override["area"].spaces.active.region_3d
        stroke = []
        for i, p in enumerate(points):
            co2d = view3d_utils.location_3d_to_region_2d(region, rv3d, p)
            if co2d is None:
                continue
            stroke.append(
                {
                    "name": "",
                    "location": p,
                    "mouse": (co2d.x, co2d.y),
                    "mouse_event": (co2d.x, co2d.y),
                    "pen_flip": bool(params.get("invert", False)),
                    "is_start": i == 0,
                    "pressure": float(params.get("pressure", 1.0)),
                    "size": float(params.get("radius_px", 50)),
                    "time": float(i),
                    "x_tilt": 0.0,
                    "y_tilt": 0.0,
                }
            )
        if not stroke:
            raise ValueError("No stroke points are visible in the viewport")
        with bpy.context.temp_override(**override):
            if params.get("brush"):
                set_sculpt_brush({"brush": params["brush"]})
            bpy.ops.sculpt.brush_stroke(
                stroke=stroke, mode="INVERT" if params.get("invert") else "NORMAL"
            )
    return {"name": obj.name, "stroke_points": len(stroke)}
