"""Lighting handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import get_object, link_object, serialize_object
from . import command


@command("create_light")
def create_light(params: dict[str, Any]):
    import bpy

    light_type = (params.get("light_type") or "POINT").upper()
    light = bpy.data.lights.new(params.get("name") or light_type.title(), light_type)
    light.energy = float(params.get("energy") or 1000.0)
    if params.get("color"):
        light.color = params["color"][:3]
    obj = bpy.data.objects.new(params.get("name") or light.name, light)
    link_object(obj, params.get("collection"))
    if params.get("location"):
        obj.location = params["location"]
    return serialize_object(obj)


@command("modify_light")
def modify_light(params: dict[str, Any]):
    obj = get_object(params["name"])
    if obj.type != "LIGHT":
        raise ValueError("Not a light")
    for key, value in (params.get("settings") or {}).items():
        if key == "location":
            obj.location = value
        elif key == "rotation":
            obj.rotation_euler = value
        elif hasattr(obj.data, key):
            setattr(obj.data, key, value)
    return serialize_object(obj)


@command("delete_light")
def delete_light(params: dict[str, Any]):
    import bpy

    if not params.get("confirmed", False):
        raise PermissionError("delete_light requires confirmed=true")
    obj = get_object(params["name"])
    if obj.type != "LIGHT":
        raise ValueError("Not a light")
    name = obj.name
    bpy.data.objects.remove(obj, do_unlink=True)
    return {"deleted": name}


@command("get_light_info")
def get_light_info(params: dict[str, Any]):
    import bpy

    if params.get("name"):
        obj = get_object(params["name"])
        if obj.type != "LIGHT":
            raise ValueError("Not a light")
        return {
            "name": obj.name,
            "type": obj.data.type,
            "energy": obj.data.energy,
            "color": list(obj.data.color),
            "location": list(obj.location),
        }
    return [
        {
            "name": o.name,
            "type": o.data.type,
            "energy": o.data.energy,
            "color": list(o.data.color),
            "location": list(o.location),
        }
        for o in bpy.context.scene.objects
        if o.type == "LIGHT"
    ]


@command("create_lighting_setup")
def create_lighting_setup(params: dict[str, Any]):
    preset = (params.get("preset") or "three_point").lower()
    target = params.get("target")
    created = []

    def add(light_type, name, location, energy, rotation=None):
        result = create_light(
            {
                "light_type": light_type,
                "name": name,
                "location": location,
                "energy": energy,
            }
        )
        if rotation:
            obj = get_object(result["name"])
            obj.rotation_euler = rotation
        created.append(result["name"])

    if preset in {"three_point", "studio", "product"}:
        add("AREA", "Key_Light", [3, -3, 3], 800 if preset != "product" else 600, [1.0, 0, 0.8])
        add("AREA", "Fill_Light", [-3, -2, 2], 300, [1.0, 0, -0.6])
        add("SPOT", "Rim_Light", [0, 3, 2], 500, [1.2, 0, 3.14])
    elif preset == "outdoor":
        add("SUN", "Sun", [0, 0, 5], 5, [0.8, 0.2, 0.1])
    elif preset == "interior":
        add("AREA", "Ceiling_Light", [0, 0, 3], 400)
        add("AREA", "Window_Light", [4, 0, 1.5], 250, [1.5, 0, -1.57])
    elif preset == "cinematic":
        add("AREA", "Cine_Key", [2, -4, 2], 700, [1.1, 0, 0.5])
        add("AREA", "Cine_Edge", [-3, 1, 1], 200)
        add("POINT", "Practical", [0, 0, 1], 50)
    else:
        raise ValueError(f"Unknown preset: {preset}")

    if target:
        try:
            focus = get_object(target)
            for name in created:
                obj = get_object(name)
                direction = focus.matrix_world.translation - obj.matrix_world.translation
                obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        except Exception:
            pass
    return {"preset": preset, "lights": created}
