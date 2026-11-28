"""Scene inspection handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import get_object, serialize_object
from . import command


def _rounded(values, digits: int = 3) -> list[float]:
    return [round(float(v), digits) for v in values]


def _compact_object(obj) -> dict[str, Any]:
    """Short per-object entry: only fields that differ from Blender's defaults.

    get_scene_info is called at the start of most sessions and its reply stays in the
    model's context, so it lists the essentials and leaves full detail to get_object_info.
    """
    entry: dict[str, Any] = {"name": obj.name, "type": obj.type}
    entry["location"] = _rounded(obj.location)
    if any(abs(v) > 1e-6 for v in obj.rotation_euler):
        entry["rotation_euler"] = _rounded(obj.rotation_euler)
    if any(abs(v - 1.0) > 1e-6 for v in obj.scale):
        entry["scale"] = _rounded(obj.scale)
    if any(abs(v) > 1e-6 for v in obj.dimensions):
        entry["dimensions"] = _rounded(obj.dimensions)
    if obj.parent:
        entry["parent"] = obj.parent.name
    if obj.type == "MESH":
        mats = [slot.material.name for slot in obj.material_slots if slot.material]
        if mats:
            entry["materials"] = mats
    mods = [m.name for m in getattr(obj, "modifiers", [])]
    if mods:
        entry["modifiers"] = mods
    if obj.hide_viewport:
        entry["hidden_viewport"] = True
    if obj.hide_render:
        entry["hidden_render"] = True
    return entry


@command("get_scene_info")
def get_scene_info(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    scene = bpy.context.scene
    limit = max(0, int(params.get("limit") or 50))
    detail = bool(params.get("detail"))
    serialize = serialize_object if detail else _compact_object
    all_objects = list(scene.objects)
    objects = [serialize(o) for o in all_objects[:limit]]
    info: dict[str, Any] = {
        "name": scene.name,
        "object_count": len(all_objects),
        "objects": objects,
        "frame_current": scene.frame_current,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "render_engine": scene.render.engine,
        "unit_system": scene.unit_settings.system,
        "active_camera": scene.camera.name if scene.camera else None,
    }
    if len(all_objects) > limit:
        info["truncated"] = (
            f"Listed {limit} of {len(all_objects)} objects. Use search_scene, "
            "get_objects(offset=...) or a higher limit for the rest."
        )
    return info


@command("get_scene_summary")
def get_scene_summary(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    scene = bpy.context.scene
    by_type: dict[str, int] = {}
    for obj in scene.objects:
        by_type[obj.type] = by_type.get(obj.type, 0) + 1
    return {
        "name": scene.name,
        "object_count": len(scene.objects),
        "objects_by_type": by_type,
        "collections": len(bpy.data.collections),
        "materials": len(bpy.data.materials),
        "frame_current": scene.frame_current,
        "render_engine": scene.render.engine,
    }


def _collection_tree(coll) -> dict[str, Any]:
    return {
        "name": coll.name,
        "objects": [o.name for o in coll.objects],
        "children": [_collection_tree(child) for child in coll.children],
    }


@command("get_scene_hierarchy")
def get_scene_hierarchy(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    return _collection_tree(bpy.context.scene.collection)


@command("get_objects")
def get_objects(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    name_filter = (params.get("name_filter") or "").lower()
    object_type = params.get("object_type")
    limit = int(params.get("limit") or 100)
    offset = int(params.get("offset") or 0)
    items = []
    for obj in bpy.context.scene.objects:
        if name_filter and name_filter not in obj.name.lower():
            continue
        if object_type and obj.type != object_type:
            continue
        items.append(serialize_object(obj))
    total = len(items)
    page = items[offset : offset + limit]
    return {"total": total, "offset": offset, "limit": limit, "objects": page}


@command("get_object_info")
def get_object_info(params: dict[str, Any]) -> dict[str, Any]:
    return serialize_object(get_object(params["name"]))


@command("get_selected_objects")
def get_selected_objects(params: dict[str, Any]) -> list[dict[str, Any]]:
    import bpy

    return [serialize_object(o) for o in bpy.context.selected_objects]


@command("get_active_object")
def get_active_object(params: dict[str, Any]) -> dict[str, Any] | None:
    import bpy

    obj = bpy.context.view_layer.objects.active
    return serialize_object(obj) if obj else None


@command("get_collections")
def get_collections(params: dict[str, Any]) -> list[dict[str, Any]]:
    import bpy

    result = []
    for coll in bpy.data.collections:
        result.append(
            {
                "name": coll.name,
                "object_count": len(coll.objects),
                "children": [c.name for c in coll.children],
            }
        )
    return result


@command("get_object_transform")
def get_object_transform(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    space = params.get("space") or "world"
    if space == "world":
        return {
            "name": obj.name,
            "location": list(obj.matrix_world.to_translation()),
            "rotation_euler": list(obj.matrix_world.to_euler()),
            "scale": list(obj.matrix_world.to_scale()),
            "space": "world",
        }
    return {
        "name": obj.name,
        "location": list(obj.location),
        "rotation_euler": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "space": "local",
    }


@command("get_mesh_statistics")
def get_mesh_statistics(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    name = params.get("name")
    if name:
        obj = get_object(name)
        if obj.type != "MESH":
            raise ValueError(f"Object is not a mesh: {name}")
        data = obj.data
        return {
            "name": name,
            "vertices": len(data.vertices),
            "edges": len(data.edges),
            "polygons": len(data.polygons),
        }
    totals = {"vertices": 0, "edges": 0, "polygons": 0, "mesh_objects": 0}
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.data:
            totals["vertices"] += len(obj.data.vertices)
            totals["edges"] += len(obj.data.edges)
            totals["polygons"] += len(obj.data.polygons)
            totals["mesh_objects"] += 1
    return totals


@command("get_scene_settings")
def get_scene_settings(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    scene = bpy.context.scene
    return {
        "unit_system": scene.unit_settings.system,
        "unit_scale": scene.unit_settings.scale_length,
        "fps": scene.render.fps,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "frame_current": scene.frame_current,
        "gravity": list(scene.gravity),
        "use_gravity": scene.use_gravity,
    }


@command("get_render_settings")
def get_render_settings(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    scene = bpy.context.scene
    render = scene.render
    cycles = getattr(scene, "cycles", None)
    eevee = getattr(scene, "eevee", None)
    result = {
        "engine": render.engine,
        "resolution_x": render.resolution_x,
        "resolution_y": render.resolution_y,
        "resolution_percentage": render.resolution_percentage,
        "filepath": render.filepath,
        "film_transparent": render.film_transparent,
        "image_settings": {
            "file_format": render.image_settings.file_format,
            "color_mode": render.image_settings.color_mode,
        },
    }
    if cycles is not None:
        result["cycles_samples"] = getattr(cycles, "samples", None)
    if eevee is not None:
        result["eevee_samples"] = getattr(eevee, "taa_render_samples", None)
    return result


@command("get_camera_info")
def get_camera_info(params: dict[str, Any]) -> Any:
    import bpy

    name = params.get("name")
    if name:
        obj = get_object(name)
        if obj.type != "CAMERA":
            raise ValueError(f"Not a camera: {name}")
        cam = obj.data
        return {
            "name": obj.name,
            "location": list(obj.location),
            "rotation_euler": list(obj.rotation_euler),
            "lens": cam.lens,
            "type": cam.type,
            "clip_start": cam.clip_start,
            "clip_end": cam.clip_end,
            "dof": {
                "use": cam.dof.use_dof,
                "focus_distance": cam.dof.focus_distance,
                "aperture_fstop": cam.dof.aperture_fstop,
                "focus_object": cam.dof.focus_object.name if cam.dof.focus_object else None,
            },
        }
    return [
        {
            "name": obj.name,
            "location": list(obj.location),
            "lens": obj.data.lens,
            "type": obj.data.type,
            "active": bpy.context.scene.camera == obj,
        }
        for obj in bpy.context.scene.objects
        if obj.type == "CAMERA"
    ]


@command("get_materials")
def get_materials(params: dict[str, Any]) -> list[dict[str, Any]]:
    import bpy

    result = []
    for mat in bpy.data.materials:
        result.append(
            {
                "name": mat.name,
                "use_nodes": mat.use_nodes,
                "users": mat.users,
            }
        )
    return result


@command("get_lights")
def get_lights(params: dict[str, Any]) -> list[dict[str, Any]]:
    import bpy

    result = []
    for obj in bpy.context.scene.objects:
        if obj.type != "LIGHT":
            continue
        light = obj.data
        result.append(
            {
                "name": obj.name,
                "type": light.type,
                "energy": light.energy,
                "color": list(light.color),
                "location": list(obj.location),
            }
        )
    return result


@command("get_modifiers")
def get_modifiers(params: dict[str, Any]) -> list[dict[str, Any]]:
    obj = get_object(params["name"])
    return [
        {"name": m.name, "type": m.type, "show_viewport": m.show_viewport} for m in obj.modifiers
    ]


@command("get_animation_info")
def get_animation_info(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    scene = bpy.context.scene
    animated = []
    for obj in scene.objects:
        if obj.animation_data and obj.animation_data.action:
            animated.append(
                {
                    "name": obj.name,
                    "action": obj.animation_data.action.name,
                    "fcurves": len(obj.animation_data.action.fcurves),
                }
            )
    return {
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "frame_current": scene.frame_current,
        "fps": scene.render.fps,
        "animated_objects": animated,
    }


@command("get_current_frame")
def get_current_frame(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    return {"frame": bpy.context.scene.frame_current}
