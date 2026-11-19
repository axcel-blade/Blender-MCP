"""Camera handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import get_object, link_object, serialize_object, set_transform
from . import command


@command("create_camera")
def create_camera(params: dict[str, Any]):
    import bpy

    cam = bpy.data.cameras.new(params.get("name") or "Camera")
    cam.lens = float(params.get("lens") or 50.0)
    obj = bpy.data.objects.new(params.get("name") or "Camera", cam)
    link_object(obj, params.get("collection"))
    set_transform(obj, params.get("location") or [0, -5, 2], params.get("rotation") or [1.1, 0, 0])
    if params.get("set_active", True):
        bpy.context.scene.camera = obj
    return serialize_object(obj)


@command("modify_camera")
def modify_camera(params: dict[str, Any]):
    obj = get_object(params["name"])
    if obj.type != "CAMERA":
        raise ValueError("Not a camera")
    for key, value in (params.get("settings") or {}).items():
        if key in {"location", "rotation", "rotation_euler"}:
            if key == "location":
                obj.location = value
            else:
                obj.rotation_euler = value
        elif hasattr(obj.data, key):
            setattr(obj.data, key, value)
    return serialize_object(obj)


@command("set_active_camera")
def set_active_camera(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    if obj.type != "CAMERA":
        raise ValueError("Not a camera")
    bpy.context.scene.camera = obj
    return {"active_camera": obj.name}


@command("focus_camera_on_object")
def focus_camera_on_object(params: dict[str, Any]):
    import mathutils

    cam = get_object(params["camera"])
    target = get_object(params["object_name"])
    direction = target.matrix_world.translation - cam.matrix_world.translation
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = target
    return {"camera": cam.name, "focus_object": target.name}


@command("frame_objects")
def frame_objects(params: dict[str, Any]):
    import bpy

    cam_name = params.get("camera")
    cam = get_object(cam_name) if cam_name else bpy.context.scene.camera
    if cam is None:
        raise ValueError("No camera available")
    names = params.get("object_names")
    bpy.ops.object.select_all(action="DESELECT")
    if names:
        for name in names:
            get_object(name).select_set(True)
    else:
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH":
                obj.select_set(True)
    bpy.context.view_layer.objects.active = cam
    # Best-effort: use view_selected if available in context
    try:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                with bpy.context.temp_override(area=area, region=area.regions[-1]):
                    bpy.ops.view3d.camera_to_view_selected()
                break
    except Exception:
        pass
    return {"camera": cam.name, "framed": names or "meshes"}


@command("configure_camera_lens")
def configure_camera_lens(params: dict[str, Any]):
    obj = get_object(params["name"])
    if obj.type != "CAMERA":
        raise ValueError("Not a camera")
    if params.get("lens") is not None:
        obj.data.lens = float(params["lens"])
    if params.get("type") is not None:
        obj.data.type = params["type"]
    if params.get("ortho_scale") is not None:
        obj.data.ortho_scale = float(params["ortho_scale"])
    return {"name": obj.name, "lens": obj.data.lens, "type": obj.data.type}


@command("configure_camera_depth_of_field")
def configure_camera_depth_of_field(params: dict[str, Any]):
    obj = get_object(params["name"])
    if obj.type != "CAMERA":
        raise ValueError("Not a camera")
    dof = obj.data.dof
    dof.use_dof = bool(params.get("enabled", True))
    if params.get("focus_object"):
        dof.focus_object = get_object(params["focus_object"])
    if params.get("focus_distance") is not None:
        dof.focus_distance = float(params["focus_distance"])
    if params.get("fstop") is not None:
        dof.aperture_fstop = float(params["fstop"])
    return {"name": obj.name, "dof": True}


@command("camera_view")
def camera_view(params: dict[str, Any]):
    import bpy

    cam = get_object(params["name"]) if params.get("name") else bpy.context.scene.camera
    if cam is None:
        raise ValueError("No camera")
    return {
        "name": cam.name,
        "location": list(cam.location),
        "rotation_euler": list(cam.rotation_euler),
        "lens": cam.data.lens,
        "type": cam.data.type,
    }
