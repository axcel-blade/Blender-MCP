"""Coherent scene generators: architecture (rooms, buildings, stairs, castles), furniture,
cities/villages, full environments, product studios, and 3D data visualisation.

Every generator puts its work in one named collection, uses real-world metre scale,
shares materials, and adds lighting + a framed camera when asked, so the result is an
intentional scene rather than loose objects."""

from __future__ import annotations

import math
import random
from typing import Any

from ..utils.objects import ensure_collection, get_object, link_object
from . import command
from .world import (
    _simple_material,
    create_terrain,
    create_vegetation,
    create_water,
    scatter_objects,
)


def _box(name, size, location, coll, mat=None, rotation=(0, 0, 0)):
    import bmesh
    import bpy
    import mathutils

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=mathutils.Vector(size), verts=bm.verts)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    link_object(obj, coll)
    obj.location = location
    obj.rotation_euler = rotation
    return obj


def _cyl(name, radius, depth, location, coll, mat=None, segments=24, radius2=None):
    import bmesh
    import bpy

    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=segments,
        radius1=radius,
        radius2=radius if radius2 is None else radius2,
        depth=depth,
    )
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    link_object(obj, coll)
    obj.location = location
    return obj


def _cut(target, cutter, apply=True):
    """Boolean difference, then drop the cutter."""
    import bpy

    mod = target.modifiers.new("Cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    if apply:
        with bpy.context.temp_override(object=target, active_object=target):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    else:
        cutter.display_type = "WIRE"
        cutter.hide_render = True


def _frame_camera(coll, center, radius, name="Scene_Camera", elevation=0.35, lens=35):
    import bpy
    import mathutils

    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_end = max(1000.0, radius * 20)
    cam = bpy.data.objects.new(name, data)
    link_object(cam, coll)
    direction = mathutils.Vector((0.7, -1.0, elevation)).normalized()
    fov = 2 * math.atan(36 / (2 * lens))
    dist = radius / math.sin(fov / 2) * 0.9
    cam.location = mathutils.Vector(center) + direction * dist
    cam.rotation_euler = (
        (mathutils.Vector(center) - cam.location).to_track_quat("-Z", "Y").to_euler()
    )
    bpy.context.scene.camera = cam
    return cam


# ------------------------------------------------------------------ architecture


@command("create_room")
def create_room(params: dict[str, Any]):
    """Room shell with floor, walls (window/door openings), optional ceiling."""
    w = float(params.get("width") or 5)
    d = float(params.get("depth") or 4)
    h = float(params.get("height") or 2.7)
    t = float(params.get("wall_thickness") or 0.2)
    coll = params.get("collection") or params.get("name") or "Room"
    ensure_collection(coll)
    wall_mat = _simple_material(
        params.get("wall_material") or "Wall_Paint",
        params.get("wall_color") or (0.85, 0.83, 0.78),
        0.8,
    )
    floor_mat = _simple_material(
        params.get("floor_material") or "Floor_Wood",
        params.get("floor_color") or (0.4, 0.25, 0.13),
        0.45,
    )
    objs = {
        "floor": _box("Floor", (w + t * 2, d + t * 2, 0.1), (0, 0, -0.05), coll, floor_mat).name
    }
    walls = {
        "north": _box("Wall_N", (w + t * 2, t, h), (0, d / 2 + t / 2, h / 2), coll, wall_mat),
        "south": _box("Wall_S", (w + t * 2, t, h), (0, -d / 2 - t / 2, h / 2), coll, wall_mat),
        "east": _box("Wall_E", (t, d, h), (w / 2 + t / 2, 0, h / 2), coll, wall_mat),
        "west": _box("Wall_W", (t, d, h), (-w / 2 - t / 2, 0, h / 2), coll, wall_mat),
    }
    openings = [dict(o, kind="window") for o in params.get("windows") or []] + [
        dict(o, kind="door") for o in params.get("doors") or []
    ]
    glass = _simple_material(
        "Window_Glass", (0.8, 0.9, 1.0), 0.02, **{"Transmission Weight": 1.0, "Transmission": 1.0}
    )
    for i, o in enumerate(openings):
        wall = walls.get(o.get("wall", "south"))
        if wall is None:
            raise ValueError("opening wall must be north, south, east or west")
        ow = float(o.get("width") or (1.2 if o["kind"] == "window" else 0.9))
        oh = float(o.get("height") or (1.2 if o["kind"] == "window" else 2.1))
        sill = float(
            o.get("sill") if o.get("sill") is not None else (0.9 if o["kind"] == "window" else 0.0)
        )
        off = float(o.get("offset") or 0.0)
        horizontal = wall.name in {"Wall_N", "Wall_S"}
        loc = (
            wall.location.x + (off if horizontal else 0),
            wall.location.y + (0 if horizontal else off),
            sill + oh / 2,
        )
        size = (ow, t * 3, oh) if horizontal else (t * 3, ow, oh)
        _cut(wall, _box(f"Cut_{i}", size, loc, coll))
        if o["kind"] == "window":
            pane = (ow, 0.02, oh) if horizontal else (0.02, ow, oh)
            _box(f"Window_{i}", pane, loc, coll, glass)
    objs["walls"] = [w_.name for w_ in walls.values()]
    if params.get("ceiling", True):
        objs["ceiling"] = _box(
            "Ceiling", (w + t * 2, d + t * 2, 0.1), (0, 0, h + 0.05), coll, wall_mat
        ).name
    if params.get("light", True):
        import bpy

        light = bpy.data.lights.new("Room_Light", "AREA")
        light.energy, light.size = 150 * w * d / 20, min(w, d) * 0.5
        lo = bpy.data.objects.new("Room_Light", light)
        link_object(lo, coll)
        lo.location = (0, 0, h - 0.05)
    return {"collection": coll, "objects": objs, "dimensions": [w, d, h], "openings": len(openings)}


FURNITURE = ("table", "chair", "sofa", "bed", "shelf", "desk", "lamp", "cabinet", "rug", "tv")


@command("create_furniture")
def create_furniture(params: dict[str, Any]):
    """Simple, correctly-scaled furniture built from blocks; joined into one object."""
    import bpy

    kind = (params.get("kind") or "table").lower()
    if kind not in FURNITURE:
        raise ValueError(f"kind must be one of {FURNITURE}")
    coll = params.get("collection") or "Furniture"
    wood = _simple_material("Furniture_Wood", params.get("color") or (0.35, 0.2, 0.1), 0.5)
    fabric = _simple_material(
        "Furniture_Fabric", params.get("fabric_color") or (0.3, 0.35, 0.45), 0.95
    )
    metal = _simple_material("Furniture_Metal", (0.6, 0.6, 0.62), 0.3, 1.0)
    parts = []

    def b(size, loc, mat=wood):
        parts.append(_box(f"{kind}_part", size, loc, coll, mat))

    def legs(w, d, h, r=0.04, mat=wood):
        for sx in (-1, 1):
            for sy in (-1, 1):
                b((r, r, h), (sx * (w / 2 - r), sy * (d / 2 - r), h / 2), mat)

    if kind == "table":
        b((1.6, 0.9, 0.05), (0, 0, 0.73))
        legs(1.6, 0.9, 0.7)
    elif kind == "desk":
        b((1.4, 0.7, 0.04), (0, 0, 0.74))
        legs(1.4, 0.7, 0.72, 0.04, metal)
    elif kind == "chair":
        b((0.45, 0.45, 0.04), (0, 0, 0.45))
        legs(0.45, 0.45, 0.43, 0.035)
        b((0.45, 0.04, 0.45), (0, 0.205, 0.7))
    elif kind == "sofa":
        b((2.0, 0.9, 0.42), (0, 0, 0.21), fabric)
        b((2.0, 0.2, 0.45), (0, 0.35, 0.65), fabric)
        b((0.2, 0.9, 0.25), (-0.9, 0, 0.55), fabric)
        b((0.2, 0.9, 0.25), (0.9, 0, 0.55), fabric)
    elif kind == "bed":
        b((1.6, 2.1, 0.3), (0, 0, 0.2))
        b((1.55, 2.0, 0.2), (0, 0, 0.45), fabric)
        b((1.6, 0.08, 0.9), (0, 1.05, 0.45))
    elif kind == "shelf":
        for i in range(5):
            b((0.9, 0.3, 0.03), (0, 0, 0.015 + i * 0.45))
        b((0.03, 0.3, 1.85), (-0.45, 0, 0.92))
        b((0.03, 0.3, 1.85), (0.45, 0, 0.92))
    elif kind == "cabinet":
        b((0.8, 0.45, 0.9), (0, 0, 0.45))
        b((0.02, 0.02, 0.12), (0.05, -0.23, 0.7), metal)
    elif kind == "lamp":
        parts.append(_cyl("lamp_base", 0.12, 0.03, (0, 0, 0.015), coll, metal))
        parts.append(_cyl("lamp_pole", 0.012, 1.5, (0, 0, 0.78), coll, metal))
        shade = _simple_material("Lamp_Shade", (1.0, 0.95, 0.85), 0.8, **{"Emission Strength": 2.0})
        parts.append(_cyl("lamp_shade", 0.22, 0.3, (0, 0, 1.6), coll, shade, radius2=0.14))
    elif kind == "rug":
        b((2.0, 1.4, 0.01), (0, 0, 0.005), fabric)
    elif kind == "tv":
        screen = _simple_material("TV_Screen", (0.01, 0.01, 0.01), 0.1)
        b((1.2, 0.05, 0.7), (0, 0, 1.0), screen)
        b((0.3, 0.2, 0.02), (0, 0, 0.6), metal)
        b((0.05, 0.05, 0.4), (0, 0, 0.8), metal)
    root = parts[0]
    if len(parts) > 1:
        with bpy.context.temp_override(
            active_object=root, selected_editable_objects=parts, object=root
        ):
            bpy.ops.object.join()
    root.name = params.get("name") or kind.title()
    root.location = params.get("location") or (0, 0, 0)
    root.rotation_euler.z = math.radians(float(params.get("rotation") or 0))
    return {"name": root.name, "kind": kind, "dimensions": list(root.dimensions)}


@command("furnish_room")
def furnish_room(params: dict[str, Any]):
    """Furnish a room by purpose: living_room, bedroom, office, dining."""
    style = (params.get("purpose") or "living_room").lower()
    w = float(params.get("width") or 5)
    d = float(params.get("depth") or 4)
    coll = params.get("collection") or "Room"
    layouts = {
        "living_room": [
            ("sofa", (0, d / 2 - 0.6, 0), 180),
            ("rug", (0, 0, 0), 0),
            ("table", (0, 0, 0), 0),
            ("tv", (0, -d / 2 + 0.3, 0), 0),
            ("lamp", (w / 2 - 0.4, d / 2 - 0.4, 0), 0),
            ("shelf", (-w / 2 + 0.3, 0, 0), 90),
        ],
        "bedroom": [
            ("bed", (0, d / 2 - 1.1, 0), 0),
            ("cabinet", (1.1, d / 2 - 0.3, 0), 0),
            ("lamp", (-1.1, d / 2 - 0.3, 0), 0),
            ("rug", (0, 0, 0), 0),
        ],
        "office": [
            ("desk", (0, d / 2 - 0.5, 0), 0),
            ("chair", (0, d / 2 - 1.1, 0), 180),
            ("shelf", (-w / 2 + 0.3, 0, 0), 90),
            ("lamp", (w / 2 - 0.4, d / 2 - 0.4, 0), 0),
        ],
        "dining": [("table", (0, 0, 0), 0)]
        + [
            ("chair", (x, y, 0), r)
            for x, y, r in ((-0.5, -0.7, 0), (0.5, -0.7, 0), (-0.5, 0.7, 180), (0.5, 0.7, 180))
        ],
    }
    if style not in layouts:
        raise ValueError(f"purpose must be one of {sorted(layouts)}")
    placed = []
    for i, (kind, loc, rot) in enumerate(layouts[style]):
        if kind == "table" and style == "living_room":
            res = create_furniture(
                {"kind": "table", "location": loc, "collection": coll, "name": f"{kind}_{i}"}
            )
            get_object(res["name"]).scale = (0.6, 0.6, 0.6)
        else:
            res = create_furniture(
                {
                    "kind": kind,
                    "location": loc,
                    "rotation": rot,
                    "collection": coll,
                    "name": f"{kind}_{i}",
                }
            )
        placed.append(res["name"])
    return {"purpose": style, "furniture": placed}


@command("create_building")
def create_building(params: dict[str, Any]):
    """Multi-storey building with window bands, floor slabs and a roof (flat/gable)."""
    import bmesh
    import bpy

    floors = max(1, int(params.get("floors") or 3))
    w = float(params.get("width") or 10)
    d = float(params.get("depth") or 8)
    fh = float(params.get("floor_height") or 3.2)
    coll = params.get("collection") or params.get("name") or "Building"
    loc = params.get("location") or (0, 0, 0)
    facade = _simple_material(
        params.get("material") or "Facade", params.get("color") or (0.7, 0.68, 0.64), 0.7
    )
    glass = _simple_material("Building_Glass", (0.25, 0.35, 0.45), 0.05, 0.3)
    body = _box(
        params.get("name") or "Building",
        (w, d, floors * fh),
        (loc[0], loc[1], loc[2] + floors * fh / 2),
        coll,
        facade,
    )
    win_w = float(params.get("window_width") or 1.2)
    spacing = float(params.get("window_spacing") or 2.5)
    cols_x = max(1, int(w / spacing))
    cols_y = max(1, int(d / spacing))
    windows = 0
    bm = bmesh.new()
    import mathutils

    for f in range(floors):
        z = f * fh + fh * 0.55
        for count, length, axis in ((cols_x, w, 0), (cols_y, d, 1)):
            for i in range(count):
                t = -length / 2 + length * (i + 0.5) / count
                for sgn in (-1, 1):
                    if axis == 0:
                        c, size = (t, sgn * (d / 2 + 0.01), z), (win_w, 0.05, fh * 0.5)
                    else:
                        c, size = (sgn * (w / 2 + 0.01), t, z), (0.05, win_w, fh * 0.5)
                    res = bmesh.ops.create_cube(bm, size=1.0)
                    bmesh.ops.scale(bm, vec=mathutils.Vector(size), verts=res["verts"])
                    bmesh.ops.translate(bm, vec=mathutils.Vector(c), verts=res["verts"])
                    windows += 1
    mesh = bpy.data.meshes.new(f"{body.name}_Windows")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(glass)
    wobj = bpy.data.objects.new(mesh.name, mesh)
    link_object(wobj, coll)
    wobj.parent = body
    wobj.location = (0, 0, -floors * fh / 2)
    roof = (params.get("roof") or "flat").lower()
    roof_mat = _simple_material(
        "Roof", (0.35, 0.15, 0.1) if roof == "gable" else (0.3, 0.3, 0.3), 0.8
    )
    if roof == "gable":
        rm = bpy.data.meshes.new(f"{body.name}_Roof")
        rh = min(w, d) * 0.35
        verts = [
            (-w / 2 - 0.3, -d / 2 - 0.3, 0),
            (w / 2 + 0.3, -d / 2 - 0.3, 0),
            (w / 2 + 0.3, d / 2 + 0.3, 0),
            (-w / 2 - 0.3, d / 2 + 0.3, 0),
            (-w / 2 - 0.3, 0, rh),
            (w / 2 + 0.3, 0, rh),
        ]
        faces = [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
        rm.from_pydata(verts, [], faces)
        rm.materials.append(roof_mat)
        ro = bpy.data.objects.new(rm.name, rm)
        link_object(ro, coll)
        ro.location = (loc[0], loc[1], loc[2] + floors * fh)
    else:
        _box(
            f"{body.name}_Roof",
            (w + 0.3, d + 0.3, 0.3),
            (loc[0], loc[1], loc[2] + floors * fh + 0.15),
            coll,
            roof_mat,
        )
    return {
        "name": body.name,
        "floors": floors,
        "height": floors * fh,
        "windows": windows,
        "collection": coll,
    }


@command("create_stairs")
def create_stairs(params: dict[str, Any]):
    import bmesh
    import bpy
    import mathutils

    steps = max(1, int(params.get("steps") or 12))
    width = float(params.get("width") or 1.0)
    rise = float(params.get("rise") or 0.18)
    run = float(params.get("run") or 0.28)
    spiral = bool(params.get("spiral", False))
    bm = bmesh.new()
    for i in range(steps):
        res = bmesh.ops.create_cube(bm, size=1.0)
        if spiral:
            bmesh.ops.scale(bm, vec=(width, run * 1.4, rise), verts=res["verts"])
            mat = mathutils.Matrix.Rotation(
                i * math.radians(float(params.get("turn_per_step") or 20)), 4, "Z"
            ) @ mathutils.Matrix.Translation((width / 2 + 0.15, 0, rise * (i + 0.5)))
            bmesh.ops.transform(bm, matrix=mat, verts=res["verts"])
        else:
            bmesh.ops.scale(bm, vec=(width, run, rise * (i + 1)), verts=res["verts"])
            bmesh.ops.translate(
                bm, vec=(0, run * (i + 0.5), rise * (i + 1) / 2), verts=res["verts"]
            )
    mesh = bpy.data.meshes.new(params.get("name") or "Stairs")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(_simple_material("Stairs_Concrete", (0.55, 0.55, 0.53), 0.85))
    obj = bpy.data.objects.new(mesh.name, mesh)
    link_object(obj, params.get("collection"))
    obj.location = params.get("location") or (0, 0, 0)
    if spiral:
        _cyl(
            f"{obj.name}_Column",
            0.15,
            rise * steps,
            (obj.location.x, obj.location.y, rise * steps / 2),
            params.get("collection"),
            mesh.materials[0],
        )
    return {"name": obj.name, "steps": steps, "total_rise": steps * rise}


@command("create_castle")
def create_castle(params: dict[str, Any]):
    """Medieval castle: curtain walls with crenellations, corner towers with conical roofs,
    a central keep, gatehouse with opening, and a courtyard."""
    import bpy

    s = float(params.get("size") or 40)
    wh = float(params.get("wall_height") or 8)
    coll = params.get("collection") or "Castle"
    ensure_collection(coll)
    stone = _simple_material("Castle_Stone", (0.45, 0.43, 0.4), 0.9)
    roof = _simple_material("Castle_Roof", (0.25, 0.1, 0.08), 0.7)
    t = 2.0
    created = []
    for name, size, loc in (
        ("Wall_N", (s, t, wh), (0, s / 2, wh / 2)),
        ("Wall_S", (s, t, wh), (0, -s / 2, wh / 2)),
        ("Wall_E", (t, s, wh), (s / 2, 0, wh / 2)),
        ("Wall_W", (t, s, wh), (-s / 2, 0, wh / 2)),
    ):
        wall = _box(name, size, loc, coll, stone)
        created.append(wall.name)
        horizontal = size[0] > size[1]
        n = int(s / 2)
        for i in range(n):
            if i % 2:
                continue
            off = -s / 2 + (i + 0.5) * s / n
            cl = (off, loc[1], wh + 0.5) if horizontal else (loc[0], off, wh + 0.5)
            created.append(
                _box(
                    f"{name}_Merlon_{i}",
                    (s / n, t, 1.0) if horizontal else (t, s / n, 1.0),
                    cl,
                    coll,
                    stone,
                ).name
            )
    tr = float(params.get("tower_radius") or 3.5)
    th = wh * 1.6
    for i, (x, y) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        created.append(_cyl(f"Tower_{i}", tr, th, (x * s / 2, y * s / 2, th / 2), coll, stone).name)
        created.append(
            _cyl(
                f"Tower_{i}_Roof",
                tr * 1.15,
                tr * 2,
                (x * s / 2, y * s / 2, th + tr),
                coll,
                roof,
                radius2=0,
            ).name
        )
    kh = wh * 2.4
    keep = _box("Keep", (s * 0.3, s * 0.3, kh), (0, s * 0.1, kh / 2), coll, stone)
    created.append(keep.name)
    for i, (x, y) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        created.append(
            _cyl(
                f"Keep_Turret_{i}",
                1.5,
                kh * 0.3,
                (x * s * 0.15, s * 0.1 + y * s * 0.15, kh + kh * 0.15),
                coll,
                stone,
            ).name
        )
        created.append(
            _cyl(
                f"Keep_Turret_{i}_Roof",
                1.8,
                3.5,
                (x * s * 0.15, s * 0.1 + y * s * 0.15, kh * 1.3 + 1.75),
                coll,
                roof,
                radius2=0,
            ).name
        )
    gate = bpy.data.objects["Wall_S"]
    _cut(gate, _box("Gate_Cut", (5, t * 3, 6), (0, -s / 2, 3), coll))
    created.append(
        _box("Gatehouse", (9, 4, wh * 1.3), (0, -s / 2 - 1, wh * 0.65), coll, stone).name
    )
    _cut(bpy.data.objects["Gatehouse"], _box("Gatehouse_Cut", (5, 8, 6), (0, -s / 2 - 1, 3), coll))
    ground = _simple_material("Courtyard", (0.3, 0.27, 0.2), 0.95)
    created.append(_box("Courtyard", (s * 1.6, s * 1.6, 0.2), (0, 0, -0.1), coll, ground).name)
    if params.get("camera", True):
        _frame_camera(coll, (0, 0, wh), s * 0.9, "Castle_Camera", elevation=0.3)
    return {"collection": coll, "objects": len(created), "size": s}


# ------------------------------------------------------------------ settlements & environments


@command("create_city")
def create_city(params: dict[str, Any]):
    """Procedural city grid: blocks of varied buildings, roads, sidewalks and street lights."""
    import bpy

    blocks = max(1, min(int(params.get("blocks") or 4), 12))
    block = float(params.get("block_size") or 30)
    road = float(params.get("road_width") or 10)
    rng = random.Random(int(params.get("seed") or 0))
    style = (params.get("style") or "modern").lower()
    coll = params.get("collection") or "City"
    ensure_collection(coll)
    total = blocks * (block + road)
    asphalt = _simple_material("Asphalt", (0.05, 0.05, 0.055), 0.9)
    walk = _simple_material("Sidewalk", (0.5, 0.5, 0.48), 0.85)
    _box("City_Ground", (total + road, total + road, 0.1), (0, 0, -0.05), coll, asphalt)
    colors = {
        "modern": [(0.6, 0.65, 0.7), (0.3, 0.33, 0.38), (0.75, 0.75, 0.72)],
        "old_town": [(0.75, 0.6, 0.45), (0.7, 0.45, 0.35), (0.85, 0.8, 0.65)],
        "sci_fi": [(0.15, 0.17, 0.22), (0.25, 0.3, 0.38), (0.6, 0.62, 0.7)],
    }.get(style, [(0.6, 0.6, 0.6)])
    count = 0
    for bx in range(blocks):
        for by in range(blocks):
            cx = -total / 2 + (bx + 0.5) * (block + road)
            cy = -total / 2 + (by + 0.5) * (block + road)
            _box(f"Block_{bx}_{by}", (block, block, 0.25), (cx, cy, 0.125), coll, walk)
            lots = 2
            lot = (block - 4) / lots
            for lx in range(lots):
                for ly in range(lots):
                    floors = rng.randint(2, 6) if style == "old_town" else rng.randint(3, 30)
                    if style == "sci_fi":
                        floors = rng.randint(8, 45)
                    bw, bd = lot * rng.uniform(0.7, 0.95), lot * rng.uniform(0.7, 0.95)
                    x = cx - block / 2 + 2 + (lx + 0.5) * lot
                    y = cy - block / 2 + 2 + (ly + 0.5) * lot
                    mat_name = f"Facade_{style}_{rng.randrange(len(colors))}"
                    create_building(
                        {
                            "name": f"Bldg_{bx}_{by}_{lx}{ly}",
                            "floors": floors,
                            "width": bw,
                            "depth": bd,
                            "floor_height": 3.2,
                            "location": (x, y, 0.25),
                            "collection": coll,
                            "material": mat_name,
                            "color": colors[int(mat_name[-1])],
                            "roof": "gable" if style == "old_town" else "flat",
                        }
                    )
                    count += 1
    lamp_mat = _simple_material("Street_Lamp", (0.2, 0.2, 0.2), 0.4, 1.0)
    for i in range(blocks + 1):
        x = -total / 2 + i * (block + road) - road / 2
        for j in range(blocks):
            y = -total / 2 + (j + 0.5) * (block + road)
            _cyl(f"Lamp_{i}_{j}", 0.1, 6, (x + road / 2 - 1, y, 3), coll, lamp_mat, segments=8)
            light = bpy.data.lights.new(f"Lamp_Light_{i}_{j}", "POINT")
            light.energy, light.color = 300, (1.0, 0.8, 0.55)
            lo = bpy.data.objects.new(light.name, light)
            link_object(lo, coll)
            lo.location = (x + road / 2 - 1, y, 6)
    if params.get("camera", True):
        _frame_camera(coll, (0, 0, 15), total * 0.6, "City_Camera", elevation=0.45)
    return {"collection": coll, "buildings": count, "extent": total, "style": style}


@command("create_village")
def create_village(params: dict[str, Any]):
    """Village of gable-roofed houses on gentle terrain with trees and a central path."""
    houses = max(1, min(int(params.get("houses") or 10), 60))
    radius = float(params.get("radius") or 40)
    rng = random.Random(int(params.get("seed") or 0))
    coll = params.get("collection") or "Village"
    ensure_collection(coll)
    terrain = create_terrain(
        {
            "name": "Village_Terrain",
            "style": "hills",
            "size": radius * 3,
            "height": 1.5,
            "resolution": 96,
            "seed": params.get("seed") or 0,
            "collection": coll,
        }
    )
    walls = [(0.85, 0.8, 0.7), (0.75, 0.65, 0.5), (0.9, 0.88, 0.82)]
    placed = []
    for i in range(houses):
        a = i / houses * math.tau + rng.uniform(-0.2, 0.2)
        r = radius * rng.uniform(0.35, 1.0)
        x, y = math.cos(a) * r, math.sin(a) * r
        res = create_building(
            {
                "name": f"House_{i}",
                "floors": rng.choice([1, 1, 2]),
                "width": rng.uniform(5, 8),
                "depth": rng.uniform(4, 6),
                "floor_height": 2.8,
                "location": (x, y, _ground_z(terrain["name"], x, y)),
                "collection": coll,
                "roof": "gable",
                "window_spacing": 2.2,
                "material": f"House_Wall_{i % 3}",
                "color": walls[i % 3],
            }
        )
        get_object(res["name"]).rotation_euler.z = a + math.pi / 2
        placed.append(res["name"])
    tree = create_vegetation(
        {"kind": "tree", "name": "Village_Tree_Src", "collection": coll, "height": 6}
    )
    scatter_objects(
        {
            "surface": terrain["name"],
            "sources": [tree["name"]],
            "count": int(params.get("trees") or 80),
            "seed": params.get("seed") or 0,
            "collection": f"{coll}_Trees",
            "min_distance": 3.0,
        }
    )
    if params.get("camera", True):
        _frame_camera(coll, (0, 0, 2), radius * 1.1, "Village_Camera", elevation=0.3)
    return {"collection": coll, "houses": placed, "terrain": terrain["name"]}


def _ground_z(name, x, y):
    import mathutils

    obj = get_object(name)
    inv = obj.matrix_world.inverted()
    origin = inv @ mathutils.Vector((x, y, 1000))
    hit, loc, *_ = obj.ray_cast(origin, (0, 0, -1))
    return (obj.matrix_world @ loc).z if hit else 0.0


ENVIRONMENTS = (
    "forest",
    "low_poly_forest",
    "pine_forest",
    "mountains",
    "desert",
    "ocean",
    "beach",
    "tropical_island",
    "winter",
    "alien_planet",
    "space",
    "fantasy",
    "swamp",
)


@command("generate_environment")
def generate_environment(params: dict[str, Any]):
    """One-call coherent environment: terrain + water + vegetation + sky/atmosphere + camera."""
    import bpy
    import mathutils

    from .world import add_atmosphere, add_clouds, set_sky, set_world_background

    preset = (params.get("preset") or "forest").lower()
    if preset not in ENVIRONMENTS:
        raise ValueError(f"preset must be one of {ENVIRONMENTS}")
    size = float(params.get("size") or 120)
    seed = int(params.get("seed") or 0)
    density = float(params.get("density") or 1.0)
    coll = params.get("collection") or f"Env_{preset}"
    ensure_collection(coll)
    report: dict[str, Any] = {"preset": preset, "collection": coll}

    def terrain(style, height, palette=None):
        args = {
            "name": f"{preset}_Terrain",
            "style": style,
            "size": size,
            "height": height,
            "resolution": int(params.get("resolution") or 160),
            "seed": seed,
            "collection": coll,
        }
        if palette:
            args["palette"] = palette
        report["terrain"] = create_terrain(args)["name"]
        return report["terrain"]

    def veg(kinds, count, max_slope=30, min_height=None, scale=(0.7, 1.3)):
        srcs = []
        for i, kind in enumerate(kinds):
            srcs.append(
                create_vegetation(
                    {
                        "kind": kind,
                        "name": f"{preset}_{kind}_src{i}",
                        "seed": seed + i,
                        "collection": f"{coll}_Sources",
                        "height": {
                            "grass_tuft": 0.4,
                            "bush": 1.2,
                            "rock": 1.5,
                            "mushroom": 0.4,
                        }.get(kind, 7),
                    }
                )["name"]
            )
        res = scatter_objects(
            {
                "surface": report["terrain"],
                "sources": srcs,
                "count": int(count * density),
                "seed": seed,
                "collection": f"{coll}_Scatter",
                "max_slope": max_slope,
                "min_height": min_height,
                "scale_range": scale,
            }
        )
        report.setdefault("scattered", 0)
        report["scattered"] += res["placed"]

    if preset in {"forest", "low_poly_forest", "pine_forest", "fantasy", "swamp"}:
        terrain("hills", 4)
        kinds = {
            "forest": ["tree", "tree", "bush", "rock"],
            "low_poly_forest": ["low_poly_tree", "pine", "rock"],
            "pine_forest": ["pine", "pine", "rock"],
            "fantasy": ["mushroom", "tree", "bush"],
            "swamp": ["dead_tree", "bush", "grass_tuft"],
        }[preset]
        veg(kinds, 400)
        if preset == "swamp":
            create_water(
                {
                    "kind": "lake",
                    "size": size,
                    "level": 0.3,
                    "collection": coll,
                    "color": (0.08, 0.1, 0.04),
                }
            )
        set_sky({"sun_elevation": 35 if preset != "fantasy" else 12, "collection": coll})
        add_atmosphere({"density": 0.004 if preset != "swamp" else 0.03})
    elif preset == "mountains":
        terrain("mountains", 25)
        veg(["pine", "rock"], 300, max_slope=25, min_height=None)
        set_sky({"sun_elevation": 20, "collection": coll})
        add_clouds({"size": size * 1.5, "altitude": 70, "collection": coll})
        add_atmosphere({"density": 0.002})
    elif preset == "desert":
        terrain("dunes", 6)
        veg(["cactus", "rock"], 60)
        set_sky({"sun_elevation": 50, "dust_density": 3.0, "collection": coll})
        add_atmosphere({"density": 0.003, "color": (0.95, 0.8, 0.6)})
    elif preset in {"ocean", "beach", "tropical_island"}:
        if preset != "ocean":
            terrain("islands", 6, [(0.85, 0.75, 0.55), (0.3, 0.5, 0.15), (0.2, 0.4, 0.1)])
            veg(["palm", "bush", "rock"], 120, min_height=1.0)
        report["water"] = create_water({"kind": "ocean", "size": size * 3, "collection": coll})[
            "name"
        ]
        set_sky({"sun_elevation": 25, "collection": coll})
        add_clouds({"size": size * 3, "altitude": 80, "coverage": 0.35, "collection": coll})
    elif preset == "winter":
        terrain("mountains", 12, [(0.85, 0.88, 0.92), (0.92, 0.94, 0.97), (1, 1, 1)])
        veg(["pine", "rock"], 250)
        from .world import set_weather

        set_weather({"weather": "snow", "area": size, "collection": coll})
    elif preset == "alien_planet":
        terrain("canyon", 15, [(0.25, 0.05, 0.3), (0.6, 0.2, 0.5), (0.2, 0.8, 0.7)])
        veg(["mushroom", "rock"], 200)
        set_world_background({"color": (0.3, 0.05, 0.25), "strength": 0.6})
        add_atmosphere({"density": 0.01, "color": (0.8, 0.4, 0.9)})
        for i, (r, loc, col) in enumerate(
            ((25, (-80, 250, 90), (0.9, 0.5, 0.2)), (10, (60, 220, 120), (0.4, 0.7, 1.0)))
        ):
            p = _uv_sphere(f"Moon_{i}", r, loc, coll, _simple_material(f"Moon_{i}_Mat", col, 0.8))
            report.setdefault("moons", []).append(p.name)
    elif preset == "space":
        _star_field_world(seed)
        sun_mat = _simple_material(
            "Star_Sun",
            (1, 0.85, 0.6),
            0.5,
            **{"Emission Color": (1, 0.8, 0.5, 1), "Emission Strength": 30.0},
        )
        _uv_sphere("Star", 15, (-120, 200, 30), coll, sun_mat)
        planet = _uv_sphere(
            "Planet", 20, (0, 0, 0), coll, _simple_material("Planet_Mat", (0.2, 0.35, 0.6), 0.6)
        )
        ring = _cyl(
            "Planet_Ring",
            34,
            0.1,
            (0, 0, 0),
            coll,
            _simple_material("Ring_Mat", (0.7, 0.6, 0.5), 0.7),
            64,
        )
        ring.rotation_euler = (math.radians(70), 0, math.radians(20))
        sun = bpy.data.objects.new("Star_Light", bpy.data.lights.new("Star_Light", "SUN"))
        link_object(sun, coll)
        sun.data.energy = 5
        sun.rotation_euler = (
            (mathutils.Vector((0, 0, 0)) - mathutils.Vector((-120, 200, 30)))
            .to_track_quat("-Z", "Y")
            .to_euler()
        )
        report["planet"] = planet.name
        _frame_camera(coll, (0, 0, 0), 45, "Space_Camera", elevation=0.15, lens=50)
        return report
    if params.get("camera", True):
        _frame_camera(coll, (0, 0, 2), size * 0.35, f"{preset}_Camera", elevation=0.12, lens=24)
        report["camera"] = f"{preset}_Camera"
    return report


def _uv_sphere(name, radius, location, coll, mat):
    import bmesh
    import bpy

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=radius)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    link_object(obj, coll)
    obj.location = location
    return obj


def _star_field_world(seed):
    from .world import _background, _world

    world = _world()
    nt = world.node_tree
    bg = _background(nt)
    noise = nt.nodes.new("ShaderNodeTexVoronoi")
    noise.inputs["Scale"].default_value = 400 + seed
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.03
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(noise.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 2.0


@command("create_product_shot")
def create_product_shot(params: dict[str, Any]):
    """Studio cyclorama backdrop + product lighting + framed camera (+ optional turntable)."""
    import bmesh
    import bpy
    import mathutils

    from .render_config import create_studio_lighting

    target = get_object(params["target"])
    coll = params.get("collection") or "Product_Studio"
    ensure_collection(coll)
    bpy.context.view_layer.update()
    corners = [target.matrix_world @ mathutils.Vector(c) for c in target.bound_box]
    lo = mathutils.Vector([min(c[i] for c in corners) for i in range(3)])
    hi = mathutils.Vector([max(c[i] for c in corners) for i in range(3)])
    size = max((hi - lo).length, 0.1)
    center = (lo + hi) / 2
    # Cyclorama: floor that curves up into a back wall.
    bm = bmesh.new()
    w = size * 6
    prof = (
        [(0, -size * 4, 0)]
        + [
            (0, size * 1.5 * math.sin(a), size * 1.5 * (1 - math.cos(a)))
            for a in (i * (math.pi / 2) / 12 for i in range(13))
        ]
        + [(0, size * 1.5, size * 5)]
    )
    left = [bm.verts.new((-w / 2, y, z)) for _, y, z in prof]
    right = [bm.verts.new((w / 2, y, z)) for _, y, z in prof]
    for i in range(len(prof) - 1):
        bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
    bm.normal_update()
    mesh = bpy.data.meshes.new("Cyclorama")
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.materials.append(
        _simple_material("Backdrop", params.get("backdrop_color") or (0.9, 0.9, 0.9), 0.6)
    )
    cyc = bpy.data.objects.new("Cyclorama", mesh)
    link_object(cyc, coll)
    cyc.location = (center.x, center.y + size * 0.5, lo.z)
    lights = create_studio_lighting(
        {"style": params.get("lighting") or "product", "target": target.name, "collection": coll}
    )
    cam = _frame_camera(
        coll,
        center,
        size * 0.75,
        "Product_Camera",
        elevation=0.25,
        lens=float(params.get("focal_length") or 85),
    )
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = target
    cam.data.dof.aperture_fstop = float(params.get("fstop") or 4.0)
    result = {
        "collection": coll,
        "camera": cam.name,
        "lights": lights["lights"],
        "backdrop": cyc.name,
    }
    if params.get("turntable"):
        from .animation_advanced import create_turntable

        result["turntable"] = create_turntable(
            {"target": target.name, "camera": cam.name, "frames": int(params.get("frames") or 120)}
        )
    return result


@command("create_data_visualization")
def create_data_visualization(params: dict[str, Any]):
    """Scientific/business 3D charts: bar (values or 2D grid), scatter (xyz points), surface
    (z = f(x, y) samples as a 2D list), line (polyline)."""
    import bmesh
    import bpy

    kind = (params.get("kind") or "bar").lower()
    data = params.get("data")
    if not data:
        raise ValueError("data is required")
    coll = params.get("collection") or f"DataViz_{kind}"
    ensure_collection(coll)
    height = float(params.get("height") or 5.0)
    created = []
    if kind == "bar":
        grid = data if isinstance(data[0], list) else [data]
        vmax = max(max(row) for row in grid) or 1
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                h = max(v / vmax * height, 0.001)
                hue = v / vmax
                mat = _simple_material(
                    f"Bar_{round(hue, 1)}", (0.2 + 0.7 * hue, 0.3, 1.0 - 0.7 * hue), 0.4
                )
                created.append(_box(f"Bar_{r}_{c}", (0.8, 0.8, h), (c, r, h / 2), coll, mat).name)
    elif kind == "scatter":
        mat = _simple_material("Scatter_Point", params.get("color") or (0.9, 0.4, 0.1), 0.4)
        bm = bmesh.new()
        import mathutils

        for p in data:
            bmesh.ops.create_icosphere(
                bm,
                subdivisions=1,
                radius=float(params.get("point_size") or 0.1),
                matrix=mathutils.Matrix.Translation(p[:3]),
            )
        created.append(_finish_mesh("Scatter_Plot", bm, coll, mat).name)
    elif kind == "surface":
        rows, cols = len(data), len(data[0])
        zmax = max(max(abs(v) for v in row) for row in data) or 1
        verts = [(c, r, data[r][c] / zmax * height) for r in range(rows) for c in range(cols)]
        faces = [
            (r * cols + c, r * cols + c + 1, (r + 1) * cols + c + 1, (r + 1) * cols + c)
            for r in range(rows - 1)
            for c in range(cols - 1)
        ]
        mesh = bpy.data.meshes.new("Surface_Plot")
        mesh.from_pydata(verts, [], faces)
        for p in mesh.polygons:
            p.use_smooth = True
        from .world import _height_material

        mesh.materials.append(
            _height_material(
                "Surface_Plot_Mat", [(0.1, 0.2, 0.8), (0.2, 0.8, 0.4), (0.95, 0.3, 0.1)], height
            )
        )
        obj = bpy.data.objects.new(mesh.name, mesh)
        link_object(obj, coll)
        created.append(obj.name)
    elif kind == "line":
        cd = bpy.data.curves.new("Line_Plot", "CURVE")
        cd.dimensions = "3D"
        cd.bevel_depth = float(params.get("thickness") or 0.05)
        sp = cd.splines.new("POLY")
        sp.points.add(len(data) - 1)
        for pt, co in zip(sp.points, data, strict=True):
            pt.co = (*co[:3], 1)
        cd.materials.append(
            _simple_material("Line_Plot_Mat", params.get("color") or (0.1, 0.6, 0.9), 0.3)
        )
        obj = bpy.data.objects.new("Line_Plot", cd)
        link_object(obj, coll)
        created.append(obj.name)
    else:
        raise ValueError("kind must be bar, scatter, surface or line")
    if params.get("axes", True):
        axis_mat = _simple_material("Axis", (0.1, 0.1, 0.1), 0.5)
        ext = float(params.get("axis_length") or 10)
        for name, size, loc in (
            ("Axis_X", (ext, 0.03, 0.03), (ext / 2, 0, 0)),
            ("Axis_Y", (0.03, ext, 0.03), (0, ext / 2, 0)),
            ("Axis_Z", (0.03, 0.03, ext), (0, 0, ext / 2)),
        ):
            created.append(_box(name, size, loc, coll, axis_mat).name)
    return {"collection": coll, "kind": kind, "objects": created}


def _finish_mesh(name, bm, coll, mat):
    import bpy

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    link_object(obj, coll)
    return obj
