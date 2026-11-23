"""World, atmosphere and environment-building handlers: backgrounds, HDRI, sky, fog,
terrain, water/ocean, scattering and vegetation."""

from __future__ import annotations

import math
import random
from typing import Any

from ..utils.context import set_enum
from ..utils.objects import get_object, link_object
from . import command


def _world():
    import bpy

    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    world = scene.world
    world.use_nodes = True
    return world


def _world_output(tree):
    out = next((n for n in tree.nodes if n.type == "OUTPUT_WORLD"), None)
    return out or tree.nodes.new("ShaderNodeOutputWorld")


def _background(tree):
    bg = next((n for n in tree.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        bg = tree.nodes.new("ShaderNodeBackground")
        tree.links.new(bg.outputs[0], _world_output(tree).inputs["Surface"])
    return bg


@command("set_world_background")
def set_world_background(params: dict[str, Any]):
    world = _world()
    tree = world.node_tree
    bg = _background(tree)
    for link in list(bg.inputs["Color"].links):
        tree.links.remove(link)
    bg.inputs["Color"].default_value = (*(params.get("color") or (0.05, 0.05, 0.05))[:3], 1.0)
    bg.inputs["Strength"].default_value = float(params.get("strength") or 1.0)
    return {"world": world.name, "color": list(bg.inputs["Color"].default_value)}


@command("set_hdri_environment")
def set_hdri_environment(params: dict[str, Any]):
    import bpy

    world = _world()
    tree = world.node_tree
    bg = _background(tree)
    env = next((n for n in tree.nodes if n.type == "TEX_ENVIRONMENT"), None) or tree.nodes.new(
        "ShaderNodeTexEnvironment"
    )
    env.image = bpy.data.images.load(params["path"], check_existing=True)
    mapping = next((n for n in tree.nodes if n.type == "MAPPING"), None) or tree.nodes.new(
        "ShaderNodeMapping"
    )
    coord = next((n for n in tree.nodes if n.type == "TEX_COORD"), None) or tree.nodes.new(
        "ShaderNodeTexCoord"
    )
    tree.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    tree.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    tree.links.new(env.outputs["Color"], bg.inputs["Color"])
    mapping.inputs["Rotation"].default_value[2] = math.radians(float(params.get("rotation") or 0.0))
    bg.inputs["Strength"].default_value = float(params.get("strength") or 1.0)
    coord.location, mapping.location, env.location = (-900, 0), (-700, 0), (-450, 0)
    if params.get("hide_background"):
        vis = getattr(world, "cycles_visibility", None)
        if vis is not None:
            vis.camera = False  # HDRI lights the scene but is not seen by the camera
    return {
        "world": world.name,
        "hdri": env.image.name,
        "strength": bg.inputs["Strength"].default_value,
    }


@command("set_sky")
def set_sky(params: dict[str, Any]):
    world = _world()
    tree = world.node_tree
    bg = _background(tree)
    sky = next((n for n in tree.nodes if n.type == "TEX_SKY"), None) or tree.nodes.new(
        "ShaderNodeTexSky"
    )
    preferred = (params.get("sky_type") or "").upper()
    for candidate in [preferred, "MULTIPLE_SCATTERING", "NISHITA", "HOSEK_WILKIE"]:
        if not candidate:
            continue
        try:
            sky.sky_type = candidate
            break
        except TypeError:
            continue
    if hasattr(sky, "sun_elevation"):
        sky.sun_elevation = math.radians(
            float(params.get("sun_elevation") if params.get("sun_elevation") is not None else 15)
        )
        sky.sun_rotation = math.radians(float(params.get("sun_rotation") or 0))
        if params.get("altitude") is not None:
            sky.altitude = float(params["altitude"])
        for key in ("air_density", "dust_density", "ozone_density", "aerosol_density"):
            if params.get(key) is not None and hasattr(sky, key):
                setattr(sky, key, float(params[key]))
    tree.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = float(params.get("strength") or 1.0)
    sky.location = (-400, 0)
    result = {"world": world.name, "sky_type": sky.sky_type}
    if params.get("add_sun", True):
        import bpy

        sun = bpy.data.objects.get("Sky_Sun")
        if sun is None:
            sun = bpy.data.objects.new("Sky_Sun", bpy.data.lights.new("Sky_Sun", "SUN"))
            link_object(sun, params.get("collection"))
        elev = math.radians(
            float(params.get("sun_elevation") if params.get("sun_elevation") is not None else 15)
        )
        sun.rotation_euler = (
            math.pi / 2 - elev,
            0,
            math.radians(float(params.get("sun_rotation") or 0)),
        )
        sun.data.energy = float(params.get("sun_strength") or 4.0)
        sun.data.angle = math.radians(0.545)
        result["sun"] = sun.name
    return result


@command("add_atmosphere")
def add_atmosphere(params: dict[str, Any]):
    """World volume fog/haze, or a local fog box (``mode='box'``) for god rays."""
    import bpy

    density = float(params.get("density") or 0.02)
    color = (*(params.get("color") or (0.8, 0.85, 0.9))[:3], 1.0)
    anisotropy = float(params.get("anisotropy") or 0.2)
    mode = (params.get("mode") or "world").lower()
    if mode == "world":
        world = _world()
        tree = world.node_tree
        vol = next(
            (n for n in tree.nodes if n.type == "PRINCIPLED_VOLUME"), None
        ) or tree.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Density"].default_value = density
        vol.inputs["Color"].default_value = color
        vol.inputs["Anisotropy"].default_value = anisotropy
        tree.links.new(vol.outputs[0], _world_output(tree).inputs["Volume"])
        return {"mode": "world", "density": density}
    size = float(params.get("size") or 50)
    mesh = bpy.data.meshes.new("Fog_Volume")
    import bmesh

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Fog_Volume", mesh)
    link_object(obj, params.get("collection"))
    obj.location = params.get("location") or (0, 0, size / 2)
    mat = bpy.data.materials.new("Fog_Volume")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = color
    vol.inputs["Anisotropy"].default_value = anisotropy
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    mesh.materials.append(mat)
    obj.display_type = "BOUNDS"
    return {"mode": "box", "object": obj.name, "density": density}


def _simple_material(name: str, color, roughness=0.6, metallic=0.0, **inputs):
    import bpy

    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        for key, value in inputs.items():
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = value
        mat.diffuse_color = (*color[:3], 1.0)
    return mat


TERRAIN_STYLES = {
    # (noise basis, octaves, lacunarity, height scale, ridged)
    "hills": (2, 4, 2.0, 1.0, False),
    "mountains": (3, 6, 2.1, 3.0, True),
    "dunes": (1, 3, 2.0, 0.5, False),
    "plateau": (2, 5, 2.0, 1.5, False),
    "canyon": (3, 5, 2.2, 2.0, True),
    "islands": (2, 5, 2.0, 1.2, False),
    "flat": (2, 2, 2.0, 0.1, False),
}


@command("create_terrain")
def create_terrain(params: dict[str, Any]):
    """Procedural fBm/ridged terrain mesh with a height-based ground material."""
    import bmesh
    import bpy
    import mathutils

    style = (params.get("style") or "hills").lower()
    if style not in TERRAIN_STYLES:
        raise ValueError(f"style must be one of {sorted(TERRAIN_STYLES)}")
    _, octaves, lac, hscale, ridged = TERRAIN_STYLES[style]
    size = float(params.get("size") or 100.0)
    res = max(8, min(int(params.get("resolution") or 128), 512))
    height = float(params.get("height") or 10.0) * hscale
    scale = float(params.get("noise_scale") or 3.0) / size
    seed = int(params.get("seed") or 0)
    offset = mathutils.Vector((seed * 17.3, seed * 9.1, seed * 3.7))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=res, y_segments=res, size=size / 2)
    noise = mathutils.noise
    for v in bm.verts:
        p = mathutils.Vector((v.co.x * scale, v.co.y * scale, 0)) + offset
        if ridged:
            h = noise.ridged_multi_fractal(
                p, 1.0, lac, octaves, 1.0, 2.0, noise_basis="PERLIN_ORIGINAL"
            )
            h = h * 0.5
        else:
            h = noise.fractal(p, 1.0, lac, octaves, noise_basis="PERLIN_ORIGINAL")
        if style == "plateau":
            h = math.tanh(h * 3.0) * 0.6
        elif style == "dunes":
            h = abs(math.sin(v.co.x * scale * 6 + noise.noise(p) * 2)) * 0.5 + h * 0.3
        elif style == "islands":
            r = math.hypot(v.co.x, v.co.y) / (size / 2)
            h = h - r * r * 1.2 + 0.2
        elif style == "canyon":
            h = -abs(h)
        v.co.z = h * height
    bm.normal_update()
    mesh = bpy.data.meshes.new(params.get("name") or f"Terrain_{style}")
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(mesh.name, mesh)
    link_object(obj, params.get("collection"))
    obj.location = params.get("location") or (0, 0, 0)
    palette = {
        "mountains": [(0.18, 0.22, 0.1), (0.35, 0.32, 0.3), (0.95, 0.95, 0.97)],
        "dunes": [(0.76, 0.6, 0.38), (0.82, 0.67, 0.45), (0.88, 0.74, 0.52)],
        "canyon": [(0.45, 0.2, 0.1), (0.62, 0.32, 0.16), (0.75, 0.48, 0.3)],
    }.get(style, [(0.12, 0.25, 0.08), (0.25, 0.35, 0.12), (0.4, 0.37, 0.3)])
    if params.get("palette"):
        palette = params["palette"]
    mesh.materials.append(_height_material(f"Terrain_{style}_Mat", palette, height))
    return {
        "name": obj.name,
        "style": style,
        "size": size,
        "vertices": len(mesh.vertices),
        "height_range": [min(v.co.z for v in mesh.vertices), max(v.co.z for v in mesh.vertices)],
    }


def _height_material(name, palette, height):
    import bpy

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mapr = nt.nodes.new("ShaderNodeMapRange")
    mapr.inputs["From Min"].default_value = -height * 0.5
    mapr.inputs["From Max"].default_value = height
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].color = (*palette[0][:3], 1)
    els[1].color = (*palette[-1][:3], 1)
    for i, col in enumerate(palette[1:-1], 1):
        e = els.new(i / (len(palette) - 1))
        e.color = (*col[:3], 1)
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    mat.diffuse_color = (*palette[len(palette) // 2][:3], 1)
    return mat


@command("create_water")
def create_water(params: dict[str, Any]):
    """Water plane (lake/pool) or animated ocean using the Ocean modifier."""
    import bpy

    kind = (params.get("kind") or "ocean").lower()
    size = float(params.get("size") or 100.0)
    mesh = bpy.data.meshes.new(params.get("name") or f"Water_{kind}")
    import bmesh

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(mesh.name, mesh)
    link_object(obj, params.get("collection"))
    obj.location = params.get("location") or (0, 0, float(params.get("level") or 0.0))
    if kind == "ocean":
        mod = obj.modifiers.new("Ocean", "OCEAN")
        mod.geometry_mode = "GENERATE"
        mod.size = 1.0
        mod.spatial_size = int(size)
        mod.resolution = int(params.get("resolution") or 12)
        mod.wave_scale = float(params.get("wave_scale") or 1.5)
        mod.wind_velocity = float(params.get("wind") or 15.0)
        mod.choppiness = float(params.get("choppiness") or 1.2)
        mod.use_foam = True
        mod.foam_layer_name = "foam"
        start = bpy.context.scene.frame_start
        end = bpy.context.scene.frame_end
        mod.time = 0
        mod.keyframe_insert("time", frame=start)
        mod.time = (end - start) / 24.0
        mod.keyframe_insert("time", frame=end)
        from .animation_advanced import iter_fcurves

        for fc in iter_fcurves(obj):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    color = params.get("color") or ((0.02, 0.12, 0.15) if kind == "ocean" else (0.05, 0.2, 0.22))
    mat = _simple_material(
        f"Water_{kind}_Mat",
        color,
        roughness=0.03,
        **{"Transmission Weight": 1.0, "Transmission": 1.0, "IOR": 1.333},
    )
    mesh.materials.append(mat)
    for p in mesh.polygons:
        p.use_smooth = True
    return {"name": obj.name, "kind": kind, "size": size}


def _sample_surface(obj, count, rng, min_z=None, max_z=None, max_slope=None):
    """Area-weighted random points on an evaluated mesh, in world space, with normals."""
    import bpy
    import mathutils

    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(dg)
    mesh = eval_obj.to_mesh()
    mesh.calc_loop_triangles()
    mw = obj.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    tris, weights = [], []
    for tri in mesh.loop_triangles:
        verts = [mw @ mesh.vertices[i].co for i in tri.vertices]
        n = (nm @ tri.normal).normalized()
        if max_slope is not None and math.degrees(n.angle(mathutils.Vector((0, 0, 1)))) > max_slope:
            continue
        tris.append((verts, n))
        weights.append(mathutils.geometry.area_tri(*verts))
    eval_obj.to_mesh_clear()
    if not tris:
        return []
    out = []
    attempts = 0
    while len(out) < count and attempts < count * 20:
        attempts += 1
        (a, b, c), n = rng.choices(tris, weights=weights, k=1)[0]
        r1, r2 = rng.random(), rng.random()
        if r1 + r2 > 1:
            r1, r2 = 1 - r1, 1 - r2
        p = a + (b - a) * r1 + (c - a) * r2
        if (min_z is not None and p.z < min_z) or (max_z is not None and p.z > max_z):
            continue
        out.append((p, n))
    return out


@command("scatter_objects")
def scatter_objects(params: dict[str, Any]):
    """Scatter linked duplicates of source objects over a surface (slope/height filters)."""
    import mathutils

    surface = get_object(params["surface"])
    sources = [get_object(n) for n in params.get("sources") or []]
    if not sources:
        raise ValueError("sources is required")
    count = max(1, min(int(params.get("count") or 100), 10000))
    rng = random.Random(int(params.get("seed") or 0))
    smin, smax = params.get("scale_range") or (0.8, 1.2)
    align = bool(params.get("align_to_normal", False))
    coll = params.get("collection") or f"Scatter_{surface.name}"
    pts = _sample_surface(
        surface,
        count,
        rng,
        params.get("min_height"),
        params.get("max_height"),
        params.get("max_slope"),
    )
    min_dist = float(params.get("min_distance") or 0.0)
    placed_pts: list = []
    created = 0
    for p, n in pts:
        if min_dist and any((p - q).length < min_dist for q in placed_pts[-400:]):
            continue
        src = rng.choice(sources)
        dup = src.copy()  # linked duplicate: shares mesh data, cheap
        link_object(dup, coll)
        dup.location = p
        s = rng.uniform(smin, smax)
        dup.scale = (src.scale.x * s, src.scale.y * s, src.scale.z * s)
        rot = mathutils.Euler((0, 0, rng.uniform(0, math.tau)))
        if align:
            q = mathutils.Vector((0, 0, 1)).rotation_difference(n)
            dup.rotation_euler = (q @ rot.to_quaternion()).to_euler()
        else:
            dup.rotation_euler = rot
        placed_pts.append(p)
        created += 1
    for src in sources:
        if params.get("hide_sources", True):
            src.hide_viewport = src.hide_render = True
    return {"surface": surface.name, "placed": created, "collection": coll}


def _mesh_obj(name, bm, coll, mat=None, smooth=False):
    import bpy

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if mat:
        mesh.materials.append(mat)
    if smooth:
        for p in mesh.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    link_object(obj, coll)
    return obj


@command("create_vegetation")
def create_vegetation(params: dict[str, Any]):
    """Procedural plants/rocks: tree, pine, low_poly_tree, palm, bush, rock, grass_tuft,
    cactus, mushroom, dead_tree. Returns one joined object (good as a scatter source)."""
    import bmesh
    import bpy
    import mathutils

    kind = (params.get("kind") or "tree").lower()
    h = float(params.get("height") or 4.0)
    rng = random.Random(int(params.get("seed") or 0))
    coll = params.get("collection") or "Vegetation"
    name = params.get("name") or kind.title()
    bark = _simple_material("Bark", (0.18, 0.11, 0.06), 0.9)
    leaf = _simple_material(
        f"Leaves_{kind}",
        params.get("leaf_color")
        or {"pine": (0.05, 0.18, 0.06), "palm": (0.15, 0.4, 0.1)}.get(kind, (0.12, 0.35, 0.08)),
        0.7,
    )
    stone = _simple_material("Rock", (0.32, 0.3, 0.28), 0.85)
    parts = []

    def add(bm, mat, smooth=False):
        parts.append(_mesh_obj(f"{name}_part", bm, coll, mat, smooth))

    def cone(r1, r2, depth, z, segs=8, mat=leaf):
        bm = bmesh.new()
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            segments=segs,
            radius1=r1,
            radius2=r2,
            depth=depth,
            matrix=mathutils.Matrix.Translation((0, 0, z + depth / 2)),
        )
        add(bm, mat)

    def blob(radius, center, mat=leaf, subdiv=2, rough=0.25):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(
            bm, subdivisions=subdiv, radius=radius, matrix=mathutils.Matrix.Translation(center)
        )
        for v in bm.verts:
            v.co += v.normal * rng.uniform(-rough, rough) * radius
        add(bm, mat, smooth=subdiv > 1)

    if kind in {"tree", "low_poly_tree", "dead_tree"}:
        cone(h * 0.06, h * 0.035, h * 0.55, 0, 8, bark)
        if kind != "dead_tree":
            sub = 1 if kind == "low_poly_tree" else 2
            blob(h * 0.3, (0, 0, h * 0.7), subdiv=sub)
            for _ in range(3):
                blob(
                    h * 0.2,
                    (
                        rng.uniform(-1, 1) * h * 0.18,
                        rng.uniform(-1, 1) * h * 0.18,
                        h * rng.uniform(0.6, 0.8),
                    ),
                    subdiv=sub,
                )
        else:
            for i in range(4):
                bm = bmesh.new()
                bmesh.ops.create_cone(
                    bm,
                    cap_ends=True,
                    segments=6,
                    radius1=h * 0.02,
                    radius2=h * 0.005,
                    depth=h * 0.3,
                )
                rot = (
                    mathutils.Euler((rng.uniform(0.5, 1.0), 0, i * math.tau / 4))
                    .to_matrix()
                    .to_4x4()
                )
                bmesh.ops.transform(
                    bm, matrix=mathutils.Matrix.Translation((0, 0, h * 0.45)) @ rot, verts=bm.verts
                )
                add(bm, bark)
    elif kind == "pine":
        cone(h * 0.05, h * 0.03, h * 0.3, 0, 8, bark)
        tiers = 4
        for i in range(tiers):
            r = h * 0.28 * (1 - i / (tiers + 0.5))
            cone(r, 0, h * 0.35, h * (0.2 + i * 0.18), 10)
    elif kind == "palm":
        cone(h * 0.05, h * 0.035, h, 0, 8, bark)
        for i in range(7):
            bm = bmesh.new()
            bmesh.ops.create_cone(
                bm, cap_ends=True, segments=4, radius1=h * 0.08, radius2=0, depth=h * 0.45
            )
            rot = mathutils.Euler((math.radians(110), 0, i * math.tau / 7)).to_matrix().to_4x4()
            bmesh.ops.transform(
                bm, matrix=mathutils.Matrix.Translation((0, 0, h)) @ rot, verts=bm.verts
            )
            add(bm, leaf)
    elif kind == "bush":
        for _ in range(5):
            blob(h * 0.2, (rng.uniform(-1, 1) * h * 0.15, rng.uniform(-1, 1) * h * 0.15, h * 0.18))
    elif kind == "rock":
        blob(h * 0.5, (0, 0, h * 0.2), stone, subdiv=2, rough=0.35)
        parts[-1].scale = (1.0, rng.uniform(0.6, 1.0), rng.uniform(0.4, 0.7))
    elif kind == "grass_tuft":
        for _ in range(12):
            bm = bmesh.new()
            bmesh.ops.create_cone(
                bm, cap_ends=False, segments=3, radius1=h * 0.02, radius2=0, depth=h
            )
            rot = (
                mathutils.Euler((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0))
                .to_matrix()
                .to_4x4()
            )
            bmesh.ops.transform(
                bm,
                matrix=mathutils.Matrix.Translation(
                    (rng.uniform(-1, 1) * h * 0.1, rng.uniform(-1, 1) * h * 0.1, h / 2)
                )
                @ rot,
                verts=bm.verts,
            )
            add(bm, leaf)
    elif kind == "cactus":
        cac = _simple_material("Cactus", (0.15, 0.4, 0.15), 0.6)
        cone(h * 0.12, h * 0.1, h, 0, 12, cac)
        for side in (-1, 1):
            bm = bmesh.new()
            bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                segments=10,
                radius1=h * 0.07,
                radius2=h * 0.06,
                depth=h * 0.35,
                matrix=mathutils.Matrix.Translation((side * h * 0.22, 0, h * 0.55)),
            )
            add(bm, cac)
    elif kind == "mushroom":
        stem = _simple_material("Mushroom_Stem", (0.9, 0.88, 0.8), 0.6)
        cap = _simple_material("Mushroom_Cap", params.get("leaf_color") or (0.7, 0.08, 0.05), 0.4)
        cone(h * 0.08, h * 0.06, h * 0.6, 0, 12, stem)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(
            bm,
            u_segments=16,
            v_segments=8,
            radius=h * 0.3,
            matrix=mathutils.Matrix.Translation((0, 0, h * 0.6)),
        )
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < h * 0.6 - 1e-4], context="VERTS")
        add(bm, cap, smooth=True)
    else:
        raise ValueError(
            "kind must be tree, low_poly_tree, dead_tree, pine, palm, bush, rock, "
            "grass_tuft, cactus or mushroom"
        )
    root = parts[0]
    if len(parts) > 1:
        with bpy.context.temp_override(
            active_object=root, selected_editable_objects=parts, object=root
        ):
            bpy.ops.object.join()
    root.name = root.data.name = name
    root.location = params.get("location") or (0, 0, 0)
    return {"name": root.name, "kind": kind, "height": h, "polygons": len(root.data.polygons)}


@command("set_weather")
def set_weather(params: dict[str, Any]):
    """Weather moods: clear, overcast, foggy, sunset, night, storm, snow, rain."""
    import bpy

    weather = (params.get("weather") or "clear").lower()
    presets = {
        "clear": dict(sky=True, elev=45, fog=0.0, strength=1.0),
        "sunset": dict(sky=True, elev=3, fog=0.005, strength=1.0),
        "overcast": dict(color=(0.55, 0.58, 0.62), strength=1.2, fog=0.01),
        "foggy": dict(color=(0.6, 0.62, 0.65), strength=0.8, fog=0.05),
        "night": dict(color=(0.005, 0.008, 0.02), strength=1.0, fog=0.0, moon=True),
        "storm": dict(color=(0.12, 0.13, 0.15), strength=0.6, fog=0.03),
        "snow": dict(color=(0.7, 0.72, 0.78), strength=1.0, fog=0.02, particles="snow"),
        "rain": dict(color=(0.25, 0.27, 0.3), strength=0.7, fog=0.02, particles="rain"),
    }
    if weather not in presets:
        raise ValueError(f"weather must be one of {sorted(presets)}")
    p = presets[weather]
    result: dict[str, Any] = {"weather": weather}
    if p.get("sky"):
        result["sky"] = set_sky({"sun_elevation": p["elev"], "strength": p["strength"]})
    else:
        result["world"] = set_world_background({"color": p["color"], "strength": p["strength"]})
    if p.get("fog"):
        add_atmosphere({"density": p["fog"]})
    if p.get("moon"):
        moon = bpy.data.objects.new("Moon_Light", bpy.data.lights.new("Moon_Light", "SUN"))
        link_object(moon, params.get("collection"))
        moon.data.energy = 0.3
        moon.data.color = (0.6, 0.7, 1.0)
        moon.rotation_euler = (math.radians(50), 0, math.radians(30))
    if p.get("particles"):
        area = float(params.get("area") or 60)
        mesh = bpy.data.meshes.new(f"{weather}_Emitter")
        import bmesh

        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=area / 2)
        bm.to_mesh(mesh)
        bm.free()
        emitter = bpy.data.objects.new(mesh.name, mesh)
        link_object(emitter, params.get("collection"))
        emitter.location = (0, 0, float(params.get("height") or 25))
        emitter.rotation_euler = (math.pi, 0, 0)
        emitter.hide_render = True
        drop = bpy.data.meshes.new(f"{weather}_Drop")
        bm = bmesh.new()
        if weather == "snow":
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.03)
        else:
            bmesh.ops.create_cone(bm, segments=3, radius1=0.005, radius2=0.005, depth=0.25)
        bm.to_mesh(drop)
        bm.free()
        drop_obj = bpy.data.objects.new(drop.name, drop)
        link_object(drop_obj, params.get("collection"))
        drop.materials.append(_simple_material(f"{weather}_Mat", (0.95, 0.95, 1.0), 0.3))
        from .physics import add_particle_system

        add_particle_system(
            {
                "name": emitter.name,
                "count": int(params.get("intensity") or 5000),
                "frame_start": -50,
                "frame_end": bpy.context.scene.frame_end,
                "lifetime": 200,
                "velocity": 0.0,
                "instance_object": drop_obj.name,
                "size": 1.0,
                "gravity": 0.05 if weather == "snow" else 1.0,
            }
        )
        drop_obj.location = (0, 0, -1000)
        result["emitter"] = emitter.name
    return result


@command("add_clouds")
def add_clouds(params: dict[str, Any]):
    """Volumetric cloud layer: a flattened box with a noise-driven Principled Volume."""
    import bmesh
    import bpy

    size = float(params.get("size") or 200)
    thick = float(params.get("thickness") or 10)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    mesh = bpy.data.meshes.new("Clouds")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Clouds", mesh)
    link_object(obj, params.get("collection"))
    obj.scale = (size, size, thick)
    obj.location = (0, 0, float(params.get("altitude") or 60))
    mat = bpy.data.materials.new("Clouds_Mat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = float(params.get("scale") or 3.0)
    noise.inputs["Detail"].default_value = 8
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cover = float(params.get("coverage") or 0.5)
    ramp.color_ramp.elements[0].position = 1 - cover
    ramp.color_ramp.elements[1].position = min(1.0, 1 - cover + 0.15)
    math_node = nt.nodes.new("ShaderNodeMath")
    math_node.operation = "MULTIPLY"
    math_node.inputs[1].default_value = float(params.get("density") or 2.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], math_node.inputs[0])
    nt.links.new(math_node.outputs[0], vol.inputs["Density"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    mesh.materials.append(mat)
    obj.display_type = "BOUNDS"
    set_enum(obj, "display_type", "BOUNDS")
    return {"name": obj.name, "altitude": obj.location.z, "coverage": cover}
