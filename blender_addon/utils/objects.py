"""Object helpers for Blender handlers."""

from __future__ import annotations

from typing import Any


def get_object(name: str):
    import bpy

    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"OBJECT_NOT_FOUND:{name}")
    return obj


def serialize_object(obj) -> dict[str, Any]:
    collections = [c.name for c in obj.users_collection]
    materials = []
    if obj.type == "MESH":
        materials = [slot.material.name for slot in obj.material_slots if slot.material]
    modifiers = [m.name for m in getattr(obj, "modifiers", [])]
    mesh_stats = None
    if obj.type == "MESH" and obj.data:
        mesh_stats = {
            "vertices": len(obj.data.vertices),
            "edges": len(obj.data.edges),
            "polygons": len(obj.data.polygons),
        }
    return {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation_euler": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
        "parent": obj.parent.name if obj.parent else None,
        "collections": collections,
        "materials": materials,
        "modifiers": modifiers,
        "visible_viewport": not obj.hide_viewport,
        "visible_render": not obj.hide_render,
        "mesh": mesh_stats,
    }


def ensure_collection(name: str, parent: str | None = None):
    import bpy

    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        if parent:
            parent_coll = bpy.data.collections.get(parent) or bpy.context.scene.collection
            if parent and bpy.data.collections.get(parent):
                bpy.data.collections[parent].children.link(coll)
            else:
                bpy.context.scene.collection.children.link(coll)
        else:
            bpy.context.scene.collection.children.link(coll)
    return coll


def link_object(obj, collection: str | None = None) -> None:
    import bpy

    if collection:
        coll = ensure_collection(collection)
        if obj.name not in coll.objects:
            coll.objects.link(obj)
        # unlink from scene root if exclusively moved
        scene_coll = bpy.context.scene.collection
        if obj.name in scene_coll.objects and coll != scene_coll:
            scene_coll.objects.unlink(obj)
    elif obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)


def set_transform(obj, location=None, rotation=None, scale=None) -> None:
    if location is not None:
        obj.location = location
    if rotation is not None:
        obj.rotation_euler = rotation
    if scale is not None:
        obj.scale = scale


def active_select(obj) -> None:
    import bpy

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
