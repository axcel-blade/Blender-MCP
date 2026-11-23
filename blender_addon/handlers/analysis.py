"""Quality control & project inspection: scene audit, mesh topology analysis, 3D-print checks
and fixes, game-asset checks/prep (LODs, lightmaps) and engine export presets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..utils.context import object_mode, require_mesh
from ..utils.objects import get_object
from . import command


def _mesh_report(obj, deep: bool = True) -> dict[str, Any]:
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    report = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "triangles": tris,
        "quads": quads,
        "ngons": len(bm.faces) - tris - quads,
        "triangle_count": sum(len(f.verts) - 2 for f in bm.faces),
        "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary),
        "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
        "loose_vertices": sum(1 for v in bm.verts if not v.link_edges),
        "loose_edges": sum(1 for e in bm.edges if not e.link_faces),
        "zero_area_faces": sum(1 for f in bm.faces if f.calc_area() < 1e-10),
    }
    if deep and len(bm.verts) < 300_000:
        import mathutils

        kd = mathutils.kdtree.KDTree(len(bm.verts))
        for v in bm.verts:
            kd.insert(v.co, v.index)
        kd.balance()
        doubles = sum(1 for v in bm.verts if len(kd.find_range(v.co, 1e-5)) > 1)
        report["overlapping_vertices"] = doubles
        bm.normal_update()
        flipped = 0
        for e in bm.edges:
            if len(e.link_faces) == 2:
                f1, f2 = e.link_faces
                v1, v2 = e.verts

                # consistent winding: shared edge traversed in opposite directions
                def order(f, v1=v1, v2=v2):
                    loops = [lp.vert for lp in f.loops]
                    i = loops.index(v1)
                    return loops[(i + 1) % len(loops)] == v2

                if order(f1) == order(f2):
                    flipped += 1
        report["inconsistent_normals_edges"] = flipped
        report["watertight"] = report["non_manifold_edges"] == 0 and report["boundary_edges"] == 0
        if report["watertight"]:
            report["volume"] = abs(bm.calc_volume(signed=True)) * abs(
                obj.matrix_world.determinant()
            )
    bm.free()
    return report


@command("analyze_mesh")
def analyze_mesh(params: dict[str, Any]):
    obj = get_object(params["name"])
    require_mesh(obj)
    report = _mesh_report(obj, deep=True)
    issues = []
    if report["ngons"]:
        issues.append(f"{report['ngons']} n-gons (may shade/deform badly; triangulate for export)")
    if report["non_manifold_edges"]:
        issues.append(f"{report['non_manifold_edges']} non-manifold edges")
    if report.get("overlapping_vertices"):
        issues.append(f"{report['overlapping_vertices']} overlapping vertices (merge_vertices)")
    if report["loose_vertices"] or report["loose_edges"]:
        issues.append("Loose geometry present (mesh_cleanup)")
    if report["zero_area_faces"]:
        issues.append(f"{report['zero_area_faces']} zero-area faces")
    if report.get("inconsistent_normals_edges"):
        issues.append("Inconsistent face winding (recalculate_normals)")
    if any(abs(s - 1) > 1e-4 for s in obj.scale):
        issues.append("Unapplied scale")
    if obj.scale.x * obj.scale.y * obj.scale.z < 0:
        issues.append("Negative scale (normals appear flipped)")
    report.update(
        {"name": obj.name, "issues": issues, "modifiers": [m.type for m in obj.modifiers]}
    )
    return report


@command("analyze_scene")
def analyze_scene(params: dict[str, Any]):
    """Whole-project audit: performance, organisation, missing data, render readiness."""
    import bpy

    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    problems, warnings, stats = [], [], {"objects": 0, "meshes": 0, "triangles": 0}
    heavy = []
    for obj in scene.objects:
        stats["objects"] += 1
        if obj.type == "MESH":
            stats["meshes"] += 1
            ev = obj.evaluated_get(dg)
            tri = sum(len(p.vertices) - 2 for p in ev.data.polygons)
            stats["triangles"] += tri
            if tri > int(params.get("heavy_threshold") or 1_000_000):
                heavy.append({"name": obj.name, "triangles": tri})
            if not obj.material_slots or all(s.material is None for s in obj.material_slots):
                warnings.append(f"{obj.name}: no material")
            if any(abs(s - 1) > 1e-4 for s in obj.scale):
                warnings.append(
                    f"{obj.name}: unapplied scale {tuple(round(s, 3) for s in obj.scale)}"
                )
        if obj.location.length > 10000:
            warnings.append(f"{obj.name}: very far from origin ({obj.location.length:.0f} units)")
        if obj.name.split(".")[0] in {
            "Cube",
            "Sphere",
            "Cylinder",
            "Plane",
            "Empty",
        } and params.get("check_naming", True):
            warnings.append(f"{obj.name}: default name")
        for mod in getattr(obj, "modifiers", []):
            if mod.type == "BOOLEAN" and mod.object is None:
                problems.append(f"{obj.name}: boolean modifier {mod.name} has no cutter")
            if (
                mod.type in {"ARMATURE", "CURVE", "LATTICE", "SHRINKWRAP"}
                and getattr(mod, "object", 1) is None
            ):
                problems.append(f"{obj.name}: {mod.type} modifier {mod.name} has no target")
    if scene.camera is None:
        problems.append("No active camera (rendering will fail)")
    lights = [o for o in scene.objects if o.type == "LIGHT"]
    if not lights and not scene.world:
        problems.append("No lights and no world")
    missing = find_missing_files({})
    if missing["missing"]:
        problems.append(f"{len(missing['missing'])} missing external files")
    orphans = sum(
        1
        for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.node_groups)
        for block in coll
        if block.users == 0
    )
    if orphans:
        warnings.append(f"{orphans} orphan data-blocks (purge to shrink the file)")
    if scene.objects and len(scene.collection.objects) > 20:
        warnings.append(
            f"{len(scene.collection.objects)} objects sit in the scene root; "
            "organise them into collections"
        )
    r = scene.render
    render = {
        "engine": r.engine,
        "resolution": [r.resolution_x, r.resolution_y, r.resolution_percentage],
        "frame_range": [scene.frame_start, scene.frame_end],
        "output": r.filepath,
    }
    if r.engine == "CYCLES":
        render["samples"] = scene.cycles.samples
        if scene.cycles.samples > 4096:
            warnings.append("Very high Cycles sample count")
    stats["lights"] = len(lights)
    stats["cameras"] = sum(1 for o in scene.objects if o.type == "CAMERA")
    stats["materials"] = len(bpy.data.materials)
    stats["images"] = len(bpy.data.images)
    stats["animated_objects"] = sum(
        1 for o in scene.objects if o.animation_data and o.animation_data.action
    )
    stats["simulations"] = sum(
        1
        for o in scene.objects
        for m in getattr(o, "modifiers", [])
        if m.type in {"CLOTH", "FLUID", "SOFT_BODY", "PARTICLE_SYSTEM"}
    ) + sum(1 for o in scene.objects if o.rigid_body)
    score = max(0, 100 - 15 * len(problems) - 2 * len(warnings))
    return {
        "scene": scene.name,
        "file": bpy.data.filepath or None,
        "stats": stats,
        "render": render,
        "heavy_objects": heavy,
        "problems": problems,
        "warnings": warnings[:100],
        "missing_files": missing["missing"],
        "health_score": score,
    }


@command("find_missing_files")
def find_missing_files(params: dict[str, Any]):
    import bpy

    missing = []
    for img in bpy.data.images:
        if img.source in {"FILE", "SEQUENCE", "MOVIE"} and not img.packed_file and img.filepath:
            path = bpy.path.abspath(img.filepath)
            if not os.path.exists(path):
                missing.append({"type": "image", "name": img.name, "path": img.filepath})
    for lib in bpy.data.libraries:
        if not os.path.exists(bpy.path.abspath(lib.filepath)):
            missing.append({"type": "library", "name": lib.name, "path": lib.filepath})
    for snd in getattr(bpy.data, "sounds", []):
        if (
            not snd.packed_file
            and snd.filepath
            and not os.path.exists(bpy.path.abspath(snd.filepath))
        ):
            missing.append({"type": "sound", "name": snd.name, "path": snd.filepath})
    for clip in bpy.data.movieclips:
        if not os.path.exists(bpy.path.abspath(clip.filepath)):
            missing.append({"type": "movieclip", "name": clip.name, "path": clip.filepath})
    for font in bpy.data.fonts:
        if (
            font.filepath != "<builtin>"
            and not font.packed_file
            and not os.path.exists(bpy.path.abspath(font.filepath))
        ):
            missing.append({"type": "font", "name": font.name, "path": font.filepath})
    return {"missing": missing, "count": len(missing)}


@command("relink_missing_files")
def relink_missing_files(params: dict[str, Any]):
    """Search a directory tree for missing images/sounds by file name and relink them."""
    import bpy

    root = Path(params["search_dir"]).expanduser()
    if not root.is_dir():
        raise ValueError("search_dir does not exist")
    index: dict[str, str] = {}
    for dirpath, _, files in os.walk(root):
        for f in files:
            index.setdefault(f.lower(), os.path.join(dirpath, f))
    fixed = []
    for block in list(bpy.data.images) + list(getattr(bpy.data, "sounds", [])):
        path = getattr(block, "filepath", "")
        if (
            path
            and not getattr(block, "packed_file", None)
            and not os.path.exists(bpy.path.abspath(path))
        ):
            hit = index.get(os.path.basename(bpy.path.abspath(path)).lower())
            if hit:
                block.filepath = hit
                if hasattr(block, "reload"):
                    block.reload()
                fixed.append({"name": block.name, "path": hit})
    return {"relinked": fixed, "remaining": find_missing_files({})["count"]}


@command("check_3d_print")
def check_3d_print(params: dict[str, Any]):
    import bmesh
    import bpy
    import mathutils

    obj = get_object(params["name"])
    require_mesh(obj)
    report = _mesh_report(obj, deep=True)
    us = bpy.context.scene.unit_settings
    to_mm = us.scale_length * 1000.0
    dims_mm = [d * to_mm for d in obj.dimensions]
    issues = []
    if not report.get("watertight"):
        issues.append("Not watertight (holes or non-manifold edges)")
    if report.get("inconsistent_normals_edges"):
        issues.append("Inconsistent normals")
    if report["loose_vertices"] or report["loose_edges"]:
        issues.append("Loose geometry")
    if report["zero_area_faces"]:
        issues.append("Degenerate faces")
    bm = bmesh.new()
    bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
    bm.transform(obj.matrix_world)
    intersections = 0
    if len(bm.faces) < 200_000:
        tree = mathutils.bvhtree.BVHTree.FromBMesh(bm, epsilon=1e-6)
        bm.faces.ensure_lookup_table()
        for a, b in tree.overlap(tree):
            if a < b and not set(bm.faces[a].verts) & set(bm.faces[b].verts):
                intersections += 1
        if intersections:
            issues.append(f"{intersections} self-intersecting face pairs")
    min_wall = float(params.get("min_thickness_mm") or 0.8) / to_mm
    thin = 0
    if len(bm.faces) < 50_000:
        tree = mathutils.bvhtree.BVHTree.FromBMesh(bm)
        bm.normal_update()
        for f in bm.faces:
            c = f.calc_center_median()
            hit = tree.ray_cast(c - f.normal * 1e-5, -f.normal, min_wall)
            if hit[0] is not None:
                thin += 1
        if thin:
            issues.append(
                f"{thin} faces closer than {params.get('min_thickness_mm') or 0.8} mm "
                "to the opposite wall"
            )
    overhang = sum(1 for f in bm.faces if f.normal.z < -0.707)
    bm.free()
    bed = params.get("build_volume_mm") or [220, 220, 250]
    if any(d > b for d, b in zip(sorted(dims_mm), sorted(bed), strict=False)):
        issues.append(f"Larger than build volume {bed} mm")
    if max(dims_mm) < 1:
        issues.append("Object is under 1 mm: check units/scale")
    return {
        "name": obj.name,
        "dimensions_mm": [round(d, 3) for d in dims_mm],
        "volume_cm3": round(report.get("volume", 0) * to_mm**3 / 1000, 3)
        if report.get("volume")
        else None,
        "watertight": report.get("watertight"),
        "self_intersections": intersections,
        "thin_faces": thin,
        "overhang_faces_over_45deg": overhang,
        "issues": issues,
        "printable": not issues,
    }


@command("prepare_for_3d_print")
def prepare_for_3d_print(params: dict[str, Any]):
    """Apply modifiers/transforms, merge doubles, fill holes, fix normals, optional voxel
    remesh for guaranteed manifold, scale to target size, set scene to millimetres."""
    import bmesh
    import bpy

    obj = get_object(params["name"])
    require_mesh(obj)
    if params.get("duplicate", True):
        dup = obj.copy()
        dup.data = obj.data.copy()
        dup.name = f"{obj.name}_print"
        for coll in obj.users_collection:
            coll.objects.link(dup)
        obj = dup
    with object_mode(obj) as override, bpy.context.temp_override(**override):
        if params.get("apply_modifiers", True):
            for mod in list(obj.modifiers):
                try:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                except RuntimeError:
                    obj.modifiers.remove(mod)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(
        bm, verts=bm.verts[:], dist=float(params.get("merge_distance") or 1e-4)
    )
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if params.get("triangulate", False):
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    if params.get("voxel_remesh"):
        obj.data.remesh_voxel_size = float(params["voxel_remesh"])
        with object_mode(obj) as override, bpy.context.temp_override(**override):
            bpy.ops.object.voxel_remesh()
    us = bpy.context.scene.unit_settings
    if params.get("set_millimetres", True):
        us.system, us.length_unit, us.scale_length = "METRIC", "MILLIMETERS", 0.001
    if params.get("target_height_mm"):
        to_mm = us.scale_length * 1000.0
        h = obj.dimensions.z * to_mm
        if h > 0:
            f = float(params["target_height_mm"]) / h
            obj.scale = (f, f, f)
            with object_mode(obj) as override, bpy.context.temp_override(**override):
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # Sit on the build plate.
    bpy.context.view_layer.update()
    min_z = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    obj.location.z -= min_z
    check = check_3d_print({"name": obj.name, "min_thickness_mm": params.get("min_thickness_mm")})
    return {"name": obj.name, "check": check}


@command("check_game_asset")
def check_game_asset(params: dict[str, Any]):
    obj = get_object(params["name"])
    require_mesh(obj)
    budget = int(params.get("triangle_budget") or 10000)
    report = _mesh_report(obj, deep=False)
    issues = []
    if report["triangle_count"] > budget:
        issues.append(f"{report['triangle_count']} triangles exceeds budget {budget}")
    if not obj.data.uv_layers:
        issues.append("No UV map")
    if len(obj.data.uv_layers) < 2 and params.get("needs_lightmap"):
        issues.append("No second UV channel for lightmaps")
    if any(abs(s - 1) > 1e-4 for s in obj.scale) or any(abs(r) > 1e-4 for r in obj.rotation_euler):
        issues.append("Unapplied rotation/scale")
    if report["ngons"]:
        issues.append("Contains n-gons")
    if len(obj.material_slots) > int(params.get("max_materials") or 4):
        issues.append(f"{len(obj.material_slots)} materials (draw calls)")
    if " " in obj.name or "." in obj.name:
        issues.append("Name contains spaces/dots; engines prefer SM_Name style")
    origin_ok = abs(min(v.co.z for v in obj.data.vertices)) < 1e-3 if obj.data.vertices else True
    if not origin_ok:
        issues.append("Origin is not at the base of the mesh")
    return {
        "name": obj.name,
        "triangles": report["triangle_count"],
        "budget": budget,
        "uv_maps": len(obj.data.uv_layers),
        "materials": len(obj.material_slots),
        "issues": issues,
        "game_ready": not issues,
    }


@command("prepare_game_asset")
def prepare_game_asset(params: dict[str, Any]):
    """Apply transforms, origin to base, smart UVs + lightmap UV, triangulate, optional LODs."""
    import bmesh
    import bpy

    from .uv import uv_unwrap

    obj = get_object(params["name"])
    require_mesh(obj)
    with object_mode(obj) as override, bpy.context.temp_override(**override):
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    min_z = min(v.co.z for v in obj.data.vertices)
    cx = sum(v.co.x for v in obj.data.vertices) / len(obj.data.vertices)
    cy = sum(v.co.y for v in obj.data.vertices) / len(obj.data.vertices)
    for v in obj.data.vertices:
        v.co.x -= cx
        v.co.y -= cy
        v.co.z -= min_z
    obj.location.x += cx
    obj.location.y += cy
    obj.location.z += min_z
    if not obj.data.uv_layers:
        uv_unwrap({"name": obj.name, "method": "smart"})
    if params.get("lightmap_uv", True) and len(obj.data.uv_layers) < 2:
        uv_unwrap({"name": obj.name, "method": "lightmap", "uv_map": "Lightmap"})
        obj.data.uv_layers.active = obj.data.uv_layers[0]
    if params.get("triangulate", True):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(obj.data)
        bm.free()
    if params.get("rename", True) and not obj.name.startswith("SM_"):
        obj.name = "SM_" + obj.name.replace(" ", "_").replace(".", "_")
    lods = []
    for i, ratio in enumerate(params.get("lod_ratios") or [], 1):
        lod = obj.copy()
        lod.data = obj.data.copy()
        lod.name = f"{obj.name}_LOD{i}"
        for coll in obj.users_collection:
            coll.objects.link(lod)
        dec = lod.modifiers.new("LOD", "DECIMATE")
        dec.ratio = float(ratio)
        with object_mode(lod) as override, bpy.context.temp_override(**override):
            bpy.ops.object.modifier_apply(modifier=dec.name)
        lods.append(
            {"name": lod.name, "triangles": sum(len(p.vertices) - 2 for p in lod.data.polygons)}
        )
    if lods:
        obj.name = f"{obj.name}_LOD0" if not obj.name.endswith("_LOD0") else obj.name
    return {
        "name": obj.name,
        "lods": lods,
        "check": check_game_asset(
            {"name": obj.name, "triangle_budget": params.get("triangle_budget")}
        ),
    }


@command("export_for_engine")
def export_for_engine(params: dict[str, Any]):
    """Engine-tuned export: unreal (FBX, cm scale), unity (FBX, axis fix), godot (glTF), web
    (GLB)."""
    import bpy

    engine = (params.get("engine") or "unreal").lower()
    path = Path(params["path"]).expanduser()
    if path.exists() and not params.get("overwrite"):
        raise PermissionError(f"Refusing to overwrite {path} without overwrite=true")
    path.parent.mkdir(parents=True, exist_ok=True)
    names = params.get("objects")
    if names:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for n in names:
            get_object(n).select_set(True)
    sel = bool(names)
    if engine in {"unreal", "unity"}:
        path = path.with_suffix(".fbx")
        kwargs = dict(
            filepath=str(path),
            use_selection=sel,
            apply_unit_scale=True,
            mesh_smooth_type="FACE",
            add_leaf_bones=False,
            bake_anim=bool(params.get("animation", True)),
            use_tspace=True,
        )
        if engine == "unreal":
            kwargs.update(
                global_scale=1.0,
                apply_scale_options="FBX_SCALE_NONE",
                axis_forward="-Y",
                axis_up="Z",
            )
        else:
            kwargs.update(
                apply_scale_options="FBX_SCALE_ALL",
                axis_forward="-Z",
                axis_up="Y",
                bake_space_transform=True,
            )
        bpy.ops.export_scene.fbx(**kwargs)
    elif engine in {"godot", "web", "gltf"}:
        path = path.with_suffix(
            ".glb" if engine != "godot" or params.get("binary", True) else ".gltf"
        )
        bpy.ops.export_scene.gltf(
            filepath=str(path),
            use_selection=sel,
            export_apply=True,
            export_animations=bool(params.get("animation", True)),
            export_draco_mesh_compression_enable=engine == "web",
        )
    else:
        raise ValueError("engine must be unreal, unity, godot, gltf or web")
    return {
        "engine": engine,
        "path": str(path),
        "size_bytes": path.stat().st_size if path.exists() else None,
    }
