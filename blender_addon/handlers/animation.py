"""Animation handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import get_object
from . import command


@command("set_current_frame")
def set_current_frame(params: dict[str, Any]):
    import bpy

    bpy.context.scene.frame_set(int(params["frame"]))
    return {"frame": bpy.context.scene.frame_current}


@command("set_animation_range")
def set_animation_range(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    scene.frame_start = int(params["frame_start"])
    scene.frame_end = int(params["frame_end"])
    return {"frame_start": scene.frame_start, "frame_end": scene.frame_end}


@command("create_keyframe")
def create_keyframe(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    frame = params.get("frame")
    if frame is not None:
        bpy.context.scene.frame_set(int(frame))
    obj.keyframe_insert(data_path=params["data_path"], index=int(params.get("index", -1)))
    return {"name": obj.name, "data_path": params["data_path"], "frame": bpy.context.scene.frame_current}


@command("set_keyframe")
def set_keyframe(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    frame = params.get("frame")
    if frame is not None:
        bpy.context.scene.frame_set(int(frame))
    data_path = params["data_path"]
    # Support simple nested paths like location / rotation_euler / scale
    parts = data_path.split(".")
    target = obj
    for part in parts[:-1]:
        target = getattr(target, part)
    setattr(target, parts[-1], params["value"])
    obj.keyframe_insert(data_path=data_path)
    return {"name": obj.name, "data_path": data_path, "frame": bpy.context.scene.frame_current}


@command("remove_keyframe")
def remove_keyframe(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    frame = params.get("frame")
    if frame is not None:
        bpy.context.scene.frame_set(int(frame))
    obj.keyframe_delete(data_path=params["data_path"])
    return {"name": obj.name, "removed": params["data_path"]}


@command("animate_location")
def animate_location(params: dict[str, Any]):
    return set_keyframe(
        {"name": params["name"], "data_path": "location", "value": params["location"], "frame": params["frame"]}
    )


@command("animate_rotation")
def animate_rotation(params: dict[str, Any]):
    return set_keyframe(
        {
            "name": params["name"],
            "data_path": "rotation_euler",
            "value": params["rotation"],
            "frame": params["frame"],
        }
    )


@command("animate_scale")
def animate_scale(params: dict[str, Any]):
    return set_keyframe(
        {"name": params["name"], "data_path": "scale", "value": params["scale"], "frame": params["frame"]}
    )


@command("inspect_animation")
def inspect_animation(params: dict[str, Any]):
    import bpy

    if params.get("name"):
        obj = get_object(params["name"])
        ad = obj.animation_data
        if not ad or not ad.action:
            return {"name": obj.name, "animated": False}
        return {
            "name": obj.name,
            "animated": True,
            "action": ad.action.name,
            "fcurves": [
                {"data_path": fc.data_path, "array_index": fc.array_index, "keyframes": len(fc.keyframe_points)}
                for fc in ad.action.fcurves
            ],
        }
    from .scene import get_animation_info

    return get_animation_info({})


@command("create_animation_preview")
def create_animation_preview(params: dict[str, Any]):
    import bpy
    from .. import screenshots

    scene = bpy.context.scene
    start = int(params.get("frame_start") or scene.frame_start)
    end = int(params.get("frame_end") or scene.frame_end)
    step = max(1, int(params.get("step") or 5))
    frames = []
    for frame in range(start, end + 1, step):
        scene.frame_set(frame)
        capture = screenshots.capture_viewport(max_size=512)
        frames.append({"frame": frame, "image_base64": capture.get("image_base64"), "mime_type": "image/png"})
    return {"frame_start": start, "frame_end": end, "step": step, "frames": frames}
