"""Collection organization handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import ensure_collection, get_object
from . import command


@command("create_collection")
def create_collection(params: dict[str, Any]):
    coll = ensure_collection(params["name"], params.get("parent"))
    return {"name": coll.name}


@command("delete_collection")
def delete_collection(params: dict[str, Any]):
    import bpy

    if not params.get("confirmed", False):
        raise PermissionError("delete_collection requires confirmed=true")
    coll = bpy.data.collections.get(params["name"])
    if coll is None:
        raise ValueError(f"Collection not found: {params['name']}")
    bpy.data.collections.remove(coll)
    return {"deleted": params["name"]}


@command("rename_collection")
def rename_collection(params: dict[str, Any]):
    import bpy

    coll = bpy.data.collections.get(params["name"])
    if coll is None:
        raise ValueError(f"Collection not found: {params['name']}")
    coll.name = params["new_name"]
    return {"name": coll.name}


@command("move_object_to_collection")
def move_object_to_collection(params: dict[str, Any]):
    obj = get_object(params["object_name"])
    coll = ensure_collection(params["collection"])
    if obj.name not in coll.objects:
        coll.objects.link(obj)
    if params.get("exclusive", True):
        for other in list(obj.users_collection):
            if other != coll:
                other.objects.unlink(obj)
    return {"object": obj.name, "collection": coll.name}


@command("get_collection_info")
def get_collection_info(params: dict[str, Any]):
    import bpy

    coll = bpy.data.collections.get(params["name"])
    if coll is None:
        raise ValueError(f"Collection not found: {params['name']}")
    return {
        "name": coll.name,
        "objects": [o.name for o in coll.objects],
        "children": [c.name for c in coll.children],
    }


@command("organize_scene")
def organize_scene(params: dict[str, Any]):
    structure = params.get("structure") or {
        "Characters": [],
        "Environment": [],
        "Props": [],
        "Lighting": [],
        "Cameras": [],
        "Background": [],
        "FX": [],
    }
    created = []
    for name, objects in structure.items():
        ensure_collection(name)
        created.append(name)
        for obj_name in objects or []:
            move_object_to_collection(
                {"object_name": obj_name, "collection": name, "exclusive": True}
            )
    return {"collections": created}


@command("create_hierarchy")
def create_hierarchy(params: dict[str, Any]):
    created = []
    parent = None
    for name in params["names"]:
        ensure_collection(name, parent)
        created.append(name)
        parent = name
    return {"hierarchy": created}
