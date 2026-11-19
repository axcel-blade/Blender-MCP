"""Modifier handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import active_select, get_object
from . import command

_TYPE_MAP = {
    "BEVEL": "BEVEL",
    "SUBSURF": "SUBSURF",
    "ARRAY": "ARRAY",
    "MIRROR": "MIRROR",
    "SOLIDIFY": "SOLIDIFY",
    "BOOLEAN": "BOOLEAN",
    "DECIMATE": "DECIMATE",
    "REMESH": "REMESH",
    "WEIGHTED_NORMAL": "WEIGHTED_NORMAL",
    "SMOOTH": "SMOOTH",
    "SHRINKWRAP": "SHRINKWRAP",
    "CURVE": "CURVE",
    "DISPLACE": "DISPLACE",
    "BUILD": "BUILD",
    "SKIN": "SKIN",
    "NODES": "NODES",
}


@command("add_modifier")
def add_modifier(params: dict[str, Any]):
    obj = get_object(params["name"])
    mod_type = str(params["modifier_type"]).upper()
    if mod_type not in _TYPE_MAP:
        raise ValueError(f"Unsupported modifier type: {mod_type}. Supported: {sorted(_TYPE_MAP)}")
    mod = obj.modifiers.new(params.get("modifier_name") or mod_type.title(), _TYPE_MAP[mod_type])
    for key, value in (params.get("settings") or {}).items():
        if hasattr(mod, key):
            setattr(mod, key, value)
    return {"object": obj.name, "modifier": mod.name, "type": mod.type}


@command("remove_modifier")
def remove_modifier(params: dict[str, Any]):
    obj = get_object(params["name"])
    mod = obj.modifiers.get(params["modifier_name"])
    if mod is None:
        raise ValueError(f"Modifier not found: {params['modifier_name']}")
    obj.modifiers.remove(mod)
    return {"object": obj.name, "removed": params["modifier_name"]}


@command("modify_modifier")
def modify_modifier(params: dict[str, Any]):
    obj = get_object(params["name"])
    mod = obj.modifiers.get(params["modifier_name"])
    if mod is None:
        raise ValueError(f"Modifier not found: {params['modifier_name']}")
    updated = []
    for key, value in (params.get("settings") or {}).items():
        if hasattr(mod, key):
            setattr(mod, key, value)
            updated.append(key)
    return {"object": obj.name, "modifier": mod.name, "updated": updated}


@command("apply_modifier")
def apply_modifier(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    mod = obj.modifiers.get(params["modifier_name"])
    if mod is None:
        raise ValueError(f"Modifier not found: {params['modifier_name']}")
    active_select(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return {"object": obj.name, "applied": params["modifier_name"]}


@command("list_modifiers")
def list_modifiers(params: dict[str, Any]):
    obj = get_object(params["name"])
    result = []
    for mod in obj.modifiers:
        info = {"name": mod.name, "type": mod.type, "show_viewport": mod.show_viewport}
        # Expose a few common properties without guessing everything
        for attr in ("levels", "render_levels", "width", "segments", "count", "thickness", "ratio"):
            if hasattr(mod, attr):
                info[attr] = getattr(mod, attr)
        result.append(info)
    return result
