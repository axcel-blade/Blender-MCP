"""Grease Pencil (2D drawing / 2D animation) for legacy GPv2 (<4.3) and GPv3 (4.3+)."""

from __future__ import annotations

import math
from typing import Any

from ..utils.objects import get_object, link_object
from . import command


def _is_v3() -> bool:
    import bpy

    return bpy.app.version >= (4, 3, 0)


def _gp_collection():
    import bpy

    if hasattr(bpy.data, "grease_pencils_v3"):
        return bpy.data.grease_pencils_v3
    return bpy.data.grease_pencils


def _gp_object(name: str):
    obj = get_object(name)
    if obj.type not in {"GPENCIL", "GREASEPENCIL"}:
        raise ValueError(f"{name} is not a Grease Pencil object")
    return obj


def _gp_material(obj, color, fill=None):
    import bpy

    key = f"GP_{'_'.join(f'{c:.2f}' for c in color[:3])}" + ("_fill" if fill else "")
    mat = bpy.data.materials.get(key)
    if mat is None:
        mat = bpy.data.materials.new(key)
        bpy.data.materials.create_gpencil_data(mat)
        mat.grease_pencil.color = (*color[:3], 1.0)
        if fill:
            mat.grease_pencil.show_fill = True
            mat.grease_pencil.fill_color = (*fill[:3], 1.0)
    slots = [m for m in obj.data.materials]
    if mat not in slots:
        obj.data.materials.append(mat)
    return list(obj.data.materials).index(mat)


@command("create_grease_pencil")
def create_grease_pencil(params: dict[str, Any]):
    import bpy

    name = params.get("name") or "GPencil"
    data = _gp_collection().new(name)
    obj = bpy.data.objects.new(name, data)
    link_object(obj, params.get("collection"))
    obj.location = params.get("location") or (0, 0, 0)
    layer = data.layers.new(params.get("layer") or "Lines")
    if not _is_v3():
        layer.frames.new(bpy.context.scene.frame_current)
    return {"name": obj.name, "type": obj.type, "layers": [layer.name if _is_v3() else layer.info]}


def _layer(data, name: str):
    for layer in data.layers:
        if (getattr(layer, "name", None) or getattr(layer, "info", None)) == name:
            return layer
    return data.layers.new(name)


def _frame(layer, frame: int):
    for f in layer.frames:
        if f.frame_number == frame:
            return f
    return layer.frames.new(frame)


@command("draw_grease_pencil_stroke")
def draw_grease_pencil_stroke(params: dict[str, Any]):
    """Draw a stroke from local-space points on a layer/frame (frames make 2D animation)."""
    import bpy

    obj = _gp_object(params["name"])
    points = params.get("points") or []
    if len(points) < 2:
        raise ValueError("points needs at least 2 [x, y, z] entries")
    radius = float(params.get("radius") or 0.02)
    color = params.get("color") or (0, 0, 0)
    mat_index = _gp_material(obj, color, params.get("fill_color"))
    frame_no = int(
        params.get("frame") if params.get("frame") is not None else bpy.context.scene.frame_current
    )
    layer = _layer(obj.data, params.get("layer") or "Lines")
    frame = _frame(layer, frame_no)
    cyclic = bool(params.get("cyclic", False))
    if _is_v3():
        drawing = frame.drawing
        drawing.add_strokes([len(points)])
        stroke = drawing.strokes[-1]
        for p, co in zip(stroke.points, points, strict=True):
            p.position = co
            p.radius = radius
            p.opacity = 1.0
        stroke.cyclic = cyclic
        stroke.material_index = mat_index
    else:
        stroke = frame.strokes.new()
        stroke.display_mode = "3DSPACE"
        stroke.line_width = int(radius * 2000)
        stroke.points.add(len(points))
        for p, co in zip(stroke.points, points, strict=True):
            p.co = co
            p.pressure = 1.0
            p.strength = 1.0
        stroke.use_cyclic = cyclic
        stroke.material_index = mat_index
    return {
        "name": obj.name,
        "layer": params.get("layer") or "Lines",
        "frame": frame_no,
        "points": len(points),
    }


def _shape_points(shape: str, size: float, sides: int, center) -> tuple[list[list[float]], bool]:
    cx, cy = center[0], center[1]
    if shape == "line":
        return [[cx - size, 0, cy], [cx + size, 0, cy]], False
    if shape in {"circle", "polygon"}:
        n = 64 if shape == "circle" else max(3, sides)
        return [
            [cx + size * math.cos(a), 0, cy + size * math.sin(a)]
            for a in (i * math.tau / n for i in range(n))
        ], True
    if shape == "rectangle":
        return [
            [cx - size, 0, cy - size * 0.6],
            [cx + size, 0, cy - size * 0.6],
            [cx + size, 0, cy + size * 0.6],
            [cx - size, 0, cy + size * 0.6],
        ], True
    if shape == "star":
        pts = []
        for i in range(sides * 2):
            r = size if i % 2 == 0 else size * 0.45
            a = math.pi / 2 + i * math.pi / sides
            pts.append([cx + r * math.cos(a), 0, cy + r * math.sin(a)])
        return pts, True
    if shape == "spiral":
        return [
            [cx + size * t / 80 * math.cos(t * 0.25), 0, cy + size * t / 80 * math.sin(t * 0.25)]
            for t in range(80)
        ], False
    if shape == "wave":
        return [
            [cx - size + 2 * size * i / 60, 0, cy + size * 0.2 * math.sin(i / 60 * math.tau * 2)]
            for i in range(61)
        ], False
    raise ValueError("shape must be line, circle, polygon, rectangle, star, spiral or wave")


@command("draw_grease_pencil_shape")
def draw_grease_pencil_shape(params: dict[str, Any]):
    shape = (params.get("shape") or "circle").lower()
    pts, cyclic = _shape_points(
        shape,
        float(params.get("size") or 1.0),
        int(params.get("sides") or 5),
        params.get("center") or (0, 0),
    )
    return draw_grease_pencil_stroke({**params, "points": pts, "cyclic": cyclic})


@command("animate_grease_pencil")
def animate_grease_pencil(params: dict[str, Any]):
    """Frame-by-frame 2D animation: ``frames=[{frame, strokes:[{points, color?, radius?}]}]``."""
    obj = _gp_object(params["name"])
    total = 0
    for entry in params.get("frames") or []:
        for stroke in entry.get("strokes") or []:
            draw_grease_pencil_stroke(
                {
                    "name": obj.name,
                    "layer": params.get("layer") or "Animation",
                    "frame": entry["frame"],
                    **stroke,
                }
            )
            total += 1
    return {"name": obj.name, "frames": len(params.get("frames") or []), "strokes": total}


@command("add_grease_pencil_modifier")
def add_grease_pencil_modifier(params: dict[str, Any]):
    obj = _gp_object(params["name"])
    mtype = params["modifier_type"].upper()
    if _is_v3():
        if not mtype.startswith("GREASE_PENCIL_"):
            mtype = f"GREASE_PENCIL_{mtype}"
        mod = obj.modifiers.new(mtype.title(), mtype)
    else:
        if not mtype.startswith("GP_"):
            mtype = f"GP_{mtype}"
        mod = obj.grease_pencil_modifiers.new(mtype.title(), mtype)
    for key, value in (params.get("settings") or {}).items():
        setattr(mod, key, value)
    return {"name": obj.name, "modifier": mod.name, "type": mtype}


@command("get_grease_pencil_info")
def get_grease_pencil_info(params: dict[str, Any]):
    obj = _gp_object(params["name"])
    layers = []
    for layer in obj.data.layers:
        frames = []
        for f in layer.frames:
            strokes = f.drawing.strokes if _is_v3() else f.strokes
            frames.append({"frame": f.frame_number, "strokes": len(strokes)})
        layers.append(
            {"name": getattr(layer, "name", None) or getattr(layer, "info", ""), "frames": frames}
        )
    return {
        "name": obj.name,
        "type": obj.type,
        "layers": layers,
        "materials": [m.name for m in obj.data.materials if m],
    }
