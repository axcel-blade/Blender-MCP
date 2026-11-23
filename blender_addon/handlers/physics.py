"""Physics & simulation handlers: rigid/soft bodies, cloth, fluids, smoke/fire, particles,
hair, force fields, gravity, fracture/destruction, baking and cache management."""

from __future__ import annotations

import contextlib
import random
from typing import Any

from ..utils.context import object_mode, require_mesh, set_enum
from ..utils.objects import get_object, link_object
from . import command

CLOTH_PRESETS = {
    "cotton": {
        "mass": 0.3,
        "tension_stiffness": 15,
        "compression_stiffness": 15,
        "bending_stiffness": 0.5,
    },
    "silk": {
        "mass": 0.15,
        "tension_stiffness": 5,
        "compression_stiffness": 5,
        "bending_stiffness": 0.05,
    },
    "denim": {
        "mass": 1.0,
        "tension_stiffness": 40,
        "compression_stiffness": 40,
        "bending_stiffness": 10,
    },
    "leather": {
        "mass": 0.4,
        "tension_stiffness": 80,
        "compression_stiffness": 80,
        "bending_stiffness": 150,
    },
    "rubber": {
        "mass": 3.0,
        "tension_stiffness": 15,
        "compression_stiffness": 15,
        "bending_stiffness": 25,
    },
}


def _apply(settings_obj, values: dict[str, Any] | None) -> list[str]:
    unknown = []
    for key, value in (values or {}).items():
        if hasattr(settings_obj, key):
            setattr(settings_obj, key, value)
        else:
            unknown.append(key)
    if unknown:
        raise ValueError(f"Unknown settings for {type(settings_obj).__name__}: {unknown}")
    return list((values or {}).keys())


@command("add_rigid_body")
def add_rigid_body(params: dict[str, Any]):
    import bpy

    names = params.get("names") or [params["name"]]
    scene = bpy.context.scene
    done = []
    for name in names:
        obj = get_object(name)
        require_mesh(obj)
        if obj.rigid_body is None:
            with object_mode(obj) as override, bpy.context.temp_override(**override):
                if scene.rigidbody_world is None:
                    bpy.ops.rigidbody.world_add()
                bpy.ops.rigidbody.object_add()
        rb = obj.rigid_body
        rb.type = (params.get("body_type") or "ACTIVE").upper()
        rb.mass = float(params.get("mass") or 1.0)
        rb.friction = float(params.get("friction") if params.get("friction") is not None else 0.5)
        rb.restitution = float(params.get("bounciness") or 0.0)
        set_enum(rb, "collision_shape", (params.get("shape") or "CONVEX_HULL").upper())
        if params.get("animated") is not None:
            rb.kinematic = bool(params["animated"])
        _apply(rb, params.get("settings"))
        done.append(obj.name)
    if params.get("frame_end") and scene.rigidbody_world:
        scene.rigidbody_world.point_cache.frame_end = int(params["frame_end"])
    return {"rigid_bodies": done, "type": (params.get("body_type") or "ACTIVE").upper()}


def _modifier(obj, mtype: str, name: str):
    mod = next((m for m in obj.modifiers if m.type == mtype), None)
    return mod or obj.modifiers.new(name, mtype)


@command("add_soft_body")
def add_soft_body(params: dict[str, Any]):
    obj = get_object(params["name"])
    mod = _modifier(obj, "SOFT_BODY", "Softbody")
    s = mod.settings
    s.mass = float(params.get("mass") or 1.0)
    s.use_goal = bool(params.get("use_goal", False))
    s.goal_default = float(params.get("goal_strength") or 0.7)
    s.pull = s.push = float(params.get("stiffness") or 0.5)
    s.use_self_collision = bool(params.get("self_collision", False))
    _apply(s, params.get("settings"))
    return {"name": obj.name, "modifier": mod.name}


@command("add_cloth")
def add_cloth(params: dict[str, Any]):
    obj = get_object(params["name"])
    require_mesh(obj)
    mod = _modifier(obj, "CLOTH", "Cloth")
    preset = (params.get("preset") or "cotton").lower()
    if preset not in CLOTH_PRESETS:
        raise ValueError(f"preset must be one of {sorted(CLOTH_PRESETS)}")
    _apply(mod.settings, CLOTH_PRESETS[preset])
    mod.collision_settings.use_self_collision = bool(params.get("self_collision", True))
    if params.get("pin_group"):
        mod.settings.vertex_group_mass = params["pin_group"]
    if params.get("pressure") is not None:
        mod.settings.use_pressure = True
        mod.settings.uniform_pressure_force = float(params["pressure"])
    _apply(mod.settings, params.get("settings"))
    return {"name": obj.name, "modifier": mod.name, "preset": preset}


@command("add_collision")
def add_collision(params: dict[str, Any]):
    done = []
    for name in params.get("names") or [params["name"]]:
        obj = get_object(name)
        _modifier(obj, "COLLISION", "Collision")
        col = obj.collision
        col.thickness_outer = float(params.get("thickness") or 0.02)
        col.cloth_friction = float(params.get("friction") or 5.0)
        col.damping = float(params.get("damping") or 0.1)
        done.append(obj.name)
    return {"colliders": done}


@command("add_fluid")
def add_fluid(params: dict[str, Any]):
    """Configure a FLUID modifier as DOMAIN, FLOW or EFFECTOR (gas or liquid)."""
    obj = get_object(params["name"])
    require_mesh(obj)
    mod = _modifier(obj, "FLUID", "Fluid")
    role = (params.get("role") or "DOMAIN").upper()
    mod.fluid_type = role
    if role == "DOMAIN":
        d = mod.domain_settings
        d.domain_type = (params.get("domain_type") or "GAS").upper()
        d.resolution_max = int(params.get("resolution") or 64)
        if d.domain_type == "LIQUID":
            d.use_mesh = True
        else:
            d.use_noise = bool(params.get("high_res_noise", False))
            d.use_dissolve_smoke = bool(params.get("dissolve", False))
        if params.get("cache_dir"):
            d.cache_directory = params["cache_dir"]
        d.cache_type = (params.get("cache_type") or "MODULAR").upper()
        d.cache_frame_end = int(params.get("frame_end") or 250)
        _apply(d, params.get("settings"))
    elif role == "FLOW":
        f = mod.flow_settings
        f.flow_type = (params.get("flow_type") or "SMOKE").upper()
        f.flow_behavior = (params.get("flow_behavior") or "INFLOW").upper()
        f.flow_source = (params.get("flow_source") or "MESH").upper()
        if params.get("surface_emission") is not None:
            f.surface_distance = float(params["surface_emission"])
        _apply(f, params.get("settings"))
    elif role == "EFFECTOR":
        e = mod.effector_settings
        e.effector_type = (params.get("effector_type") or "COLLISION").upper()
        _apply(e, params.get("settings"))
    else:
        raise ValueError("role must be DOMAIN, FLOW or EFFECTOR")
    return {"name": obj.name, "role": role}


@command("quick_effect")
def quick_effect(params: dict[str, Any]):
    """Blender quick effects: smoke, fire, smoke_fire, liquid, explode, fur."""
    import bpy

    objs = [get_object(n) for n in (params.get("names") or [params["name"]])]
    effect = (params.get("effect") or "smoke").lower()
    before = set(bpy.data.objects)
    with object_mode(objs[0]) as override, bpy.context.temp_override(**override):
        for o in objs:
            o.select_set(True)
        if effect in {"smoke", "fire", "smoke_fire"}:
            style = {"smoke": "SMOKE", "fire": "FIRE", "smoke_fire": "BOTH"}[effect]
            bpy.ops.object.quick_smoke(style=style, show_flows=False)
        elif effect == "liquid":
            bpy.ops.object.quick_liquid(show_flows=False)
        elif effect == "explode":
            bpy.ops.object.quick_explode(
                amount=int(params.get("pieces") or 100),
                frame_start=int(params.get("frame_start") or 1),
                frame_end=int(params.get("frame_end") or 10),
            )
        elif effect == "fur":
            bpy.ops.object.quick_fur(density=(params.get("density") or "MEDIUM").upper())
        else:
            raise ValueError("effect must be smoke, fire, smoke_fire, liquid, explode or fur")
    created = [o.name for o in set(bpy.data.objects) - before]
    return {"effect": effect, "objects": [o.name for o in objs], "created": created}


@command("add_particle_system")
def add_particle_system(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    mod = obj.modifiers.new(params.get("system_name") or "Particles", "PARTICLE_SYSTEM")
    ps = mod.particle_system
    s = ps.settings
    s.type = (params.get("particle_type") or "EMITTER").upper()
    s.count = int(params.get("count") or 1000)
    ps.seed = int(params.get("seed") or 0)
    if s.type == "EMITTER":
        s.frame_start = float(params.get("frame_start") or 1)
        s.frame_end = float(params.get("frame_end") or 200)
        s.lifetime = float(params.get("lifetime") or 50)
        s.normal_factor = float(
            params.get("velocity") if params.get("velocity") is not None else 1.0
        )
        s.factor_random = float(params.get("random_velocity") or 0.0)
        if params.get("gravity") is not None:
            s.effector_weights.gravity = float(params["gravity"])
    else:
        s.hair_length = float(params.get("hair_length") or 0.2)
        s.hair_step = int(params.get("segments") or 5)
        if params.get("children"):
            s.child_type = "INTERPOLATED"
            # child_nbr was renamed child_percent (viewport amount) in newer Blender.
            for attr in ("child_percent", "child_nbr"):
                if hasattr(s, attr):
                    setattr(s, attr, int(params["children"]))
                    break
            s.rendered_child_count = int(params["children"])
        s.use_advanced_hair = True
        s.brownian_factor = float(params.get("randomness") or 0.0)
    if params.get("instance_object"):
        s.render_type = "OBJECT"
        s.instance_object = get_object(params["instance_object"])
        s.particle_size = float(params.get("size") or 0.1)
        s.size_random = float(params.get("size_random") or 0.0)
        s.use_rotations = True
        s.rotation_mode = "NOR"
        s.phase_factor_random = float(params.get("random_rotation") or 0.0)
    elif params.get("instance_collection"):
        coll = bpy.data.collections.get(params["instance_collection"])
        if coll is None:
            raise ValueError("instance_collection not found")
        s.render_type = "COLLECTION"
        s.instance_collection = coll
        s.particle_size = float(params.get("size") or 0.1)
    if params.get("density_group"):
        ps.vertex_group_density = params["density_group"]
    _apply(s, params.get("settings"))
    return {
        "name": obj.name,
        "particle_system": ps.name,
        "settings": s.name,
        "type": s.type,
        "count": s.count,
    }


@command("add_force_field")
def add_force_field(params: dict[str, Any]):
    import bpy

    ftype = (params.get("field_type") or "WIND").upper()
    # Objects made with bpy.data have no FieldSettings (obj.field is None); the operator
    # creates a proper force-field empty.
    with bpy.context.temp_override(**_scene_override()):
        bpy.ops.object.effector_add(type=ftype, location=params.get("location") or (0, 0, 0))
    obj = bpy.context.view_layer.objects.active
    obj.name = params.get("name") or f"{ftype.title()}_Field"
    if params.get("collection"):
        for coll in list(obj.users_collection):
            coll.objects.unlink(obj)
        link_object(obj, params["collection"])
    obj.rotation_euler = params.get("rotation") or (0, 0, 0)
    obj.field.strength = float(params.get("strength") or 5.0)
    if params.get("flow") is not None:
        obj.field.flow = float(params["flow"])
    if params.get("noise") is not None:
        obj.field.noise = float(params["noise"])
    if params.get("falloff"):
        obj.field.falloff_type = params["falloff"].upper()
    _apply(obj.field, params.get("settings"))
    return {"name": obj.name, "field_type": ftype, "strength": obj.field.strength}


def _scene_override() -> dict[str, Any]:
    from ..utils.context import view3d_override

    return view3d_override()


@command("set_gravity")
def set_gravity(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    scene.use_gravity = bool(params.get("enabled", True))
    if params.get("gravity") is not None:
        scene.gravity = params["gravity"]
    return {"use_gravity": scene.use_gravity, "gravity": list(scene.gravity)}


@command("fracture_object")
def fracture_object(params: dict[str, Any]):
    """Voronoi fracture with bmesh bisection (no add-on required). Returns chunk objects."""
    import bmesh
    import bpy
    import mathutils

    src = get_object(params["name"])
    require_mesh(src)
    pieces = max(2, min(int(params.get("pieces") or 12), 150))
    rng = random.Random(int(params.get("seed") or 0))
    dg = bpy.context.evaluated_depsgraph_get()
    base = bmesh.new()
    base.from_object(src, dg)
    bbox = [mathutils.Vector(c) for c in src.bound_box]
    lo = mathutils.Vector([min(c[i] for c in bbox) for i in range(3)])
    hi = mathutils.Vector([max(c[i] for c in bbox) for i in range(3)])
    if params.get("impact_point"):
        center = src.matrix_world.inverted() @ mathutils.Vector(params["impact_point"])
        spread = (hi - lo).length * 0.35
        seeds = [
            center + mathutils.Vector([rng.gauss(0, spread) for _ in range(3)])
            for _ in range(pieces)
        ]
        seeds = [mathutils.Vector([max(lo[i], min(hi[i], s[i])) for i in range(3)]) for s in seeds]
    else:
        seeds = [
            mathutils.Vector([rng.uniform(lo[i], hi[i]) for i in range(3)]) for _ in range(pieces)
        ]
    coll_name = params.get("collection") or f"{src.name}_Fracture"
    chunks = []
    for i, seed in enumerate(seeds):
        bm = base.copy()
        for j, other in enumerate(seeds):
            if i == j:
                continue
            normal = (other - seed).normalized()
            mid = (seed + other) * 0.5
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            res = bmesh.ops.bisect_plane(
                bm, geom=geom, plane_co=mid, plane_no=normal, clear_outer=True
            )
            cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if cut_edges:
                bmesh.ops.holes_fill(bm, edges=cut_edges)
            if not bm.verts:
                break
        if len(bm.faces) < 4:
            bm.free()
            continue
        mesh = bpy.data.meshes.new(f"{src.name}_chunk_{i:03d}")
        bm.to_mesh(mesh)
        bm.free()
        for mat in src.data.materials:
            mesh.materials.append(mat)
        chunk = bpy.data.objects.new(mesh.name, mesh)
        chunk.matrix_world = src.matrix_world.copy()
        link_object(chunk, coll_name)
        with (
            bpy.context.temp_override(
                active_object=chunk, selected_editable_objects=[chunk], object=chunk
            ),
            contextlib.suppress(Exception),
        ):  # origin is cosmetic; keep the chunk
            bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        chunks.append(chunk.name)
    base.free()
    if params.get("hide_original", True):
        src.hide_viewport = src.hide_render = True
    if params.get("rigid_body", True) and chunks:
        add_rigid_body(
            {
                "names": chunks,
                "body_type": "ACTIVE",
                "mass": params.get("chunk_mass") or 0.5,
                "shape": "CONVEX_HULL",
            }
        )
    return {"source": src.name, "chunks": chunks, "collection": coll_name}


@command("bake_simulation")
def bake_simulation(params: dict[str, Any]):
    import bpy

    kind = (params.get("kind") or "all").lower()
    scene = bpy.context.scene
    if params.get("frame_start") is not None:
        scene.frame_start = int(params["frame_start"])
    if params.get("frame_end") is not None:
        scene.frame_end = int(params["frame_end"])
    if kind == "fluid":
        obj = get_object(params["name"])
        with object_mode(obj) as override, bpy.context.temp_override(**override):
            bpy.ops.fluid.bake_all()
        return {"baked": "fluid", "domain": obj.name}
    if kind == "rigid_body":
        with bpy.context.temp_override(scene=scene, point_cache=scene.rigidbody_world.point_cache):
            bpy.ops.ptcache.bake(bake=True)
        return {"baked": "rigid_body"}
    if kind == "geometry_nodes":
        bpy.ops.object.simulation_nodes_cache_bake(selected=False)
        return {"baked": "geometry_nodes"}
    bpy.ops.ptcache.bake_all(bake=True)
    return {"baked": "all_point_caches", "frame_range": [scene.frame_start, scene.frame_end]}


@command("free_simulation_cache")
def free_simulation_cache(params: dict[str, Any]):
    import bpy

    if params.get("name"):
        obj = get_object(params["name"])
        if any(m.type == "FLUID" and m.fluid_type == "DOMAIN" for m in obj.modifiers):
            with object_mode(obj) as override, bpy.context.temp_override(**override):
                bpy.ops.fluid.free_all()
            return {"freed": "fluid", "domain": obj.name}
    bpy.ops.ptcache.free_bake_all()
    return {"freed": "all_point_caches"}


@command("get_physics_info")
def get_physics_info(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    objs = [get_object(params["name"])] if params.get("name") else list(scene.objects)
    out = []
    for o in objs:
        entry: dict[str, Any] = {"name": o.name}
        if o.rigid_body:
            entry["rigid_body"] = {
                "type": o.rigid_body.type,
                "mass": o.rigid_body.mass,
                "shape": o.rigid_body.collision_shape,
            }
        sims = [
            m
            for m in getattr(o, "modifiers", [])
            if m.type
            in {
                "CLOTH",
                "SOFT_BODY",
                "FLUID",
                "COLLISION",
                "PARTICLE_SYSTEM",
                "DYNAMIC_PAINT",
                "OCEAN",
            }
        ]
        if sims:
            entry["simulations"] = []
            for m in sims:
                item = {"modifier": m.name, "type": m.type}
                if m.type == "FLUID":
                    item["role"] = m.fluid_type
                if m.type == "PARTICLE_SYSTEM":
                    item["particles"] = {
                        "type": m.particle_system.settings.type,
                        "count": m.particle_system.settings.count,
                    }
                cache = getattr(getattr(m, "point_cache", None), "is_baked", None)
                if cache is not None:
                    item["baked"] = cache
                entry["simulations"].append(item)
        if o.field and o.field.type != "NONE":
            entry["force_field"] = {"type": o.field.type, "strength": o.field.strength}
        if len(entry) > 1:
            out.append(entry)
    rbw = scene.rigidbody_world
    return {
        "gravity": list(scene.gravity),
        "use_gravity": scene.use_gravity,
        "rigid_body_world": {"enabled": rbw.enabled, "frame_end": rbw.point_cache.frame_end}
        if rbw
        else None,
        "objects": out,
    }
