"""Advanced animation: generic property keys, interpolation, loops, curve modifiers,
motion paths, baking, follow-path, turntables, motion graphics, mocap retargeting."""

from __future__ import annotations

import math
from typing import Any

from ..utils.context import object_mode
from ..utils.objects import get_object, link_object
from . import command


def iter_fcurves(id_block):
    """Yield F-curves for an ID's action across legacy and 4.4+ layered (slotted) actions."""
    anim = getattr(id_block, "animation_data", None)
    action = anim.action if anim else None
    if action is None:
        return
    layers = getattr(action, "layers", None)
    if layers and len(layers):
        slot = getattr(anim, "action_slot", None)
        for layer in layers:
            for strip in layer.strips:
                bags = (
                    [strip.channelbag(slot)]
                    if slot is not None and hasattr(strip, "channelbag")
                    else list(getattr(strip, "channelbags", []))
                )
                for bag in bags:
                    if bag is not None:
                        yield from bag.fcurves
        return
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        yield from legacy


def _resolve_owner(params: dict[str, Any]):
    """Return the ID that owns ``data_path``: object, its data, a material, world or scene."""
    import bpy

    target = (params.get("target") or "object").lower()
    if target == "scene":
        return bpy.context.scene
    if target == "world":
        return bpy.context.scene.world
    if target == "material":
        mat = bpy.data.materials.get(params.get("material") or "")
        if mat is None:
            raise ValueError("material not found")
        return mat.node_tree if params.get("node_tree", True) and mat.node_tree else mat
    obj = get_object(params["name"])
    return obj.data if target == "data" else obj


@command("animate_property")
def animate_property(params: dict[str, Any]):
    """Keyframe any animatable property: ``keyframes=[{frame, value, interpolation?}]``."""
    owner = _resolve_owner(params)
    path = params["data_path"]
    index = int(params.get("index", -1))
    keys = params.get("keyframes") or []
    if not keys:
        raise ValueError("keyframes is required")
    owner.path_resolve(path)  # raises a readable error for bad paths
    for key in keys:
        value = key["value"]
        if index >= 0:
            prop = owner.path_resolve(path)
            prop[index] = value
        else:
            _set_path(owner, path, value)
        owner.keyframe_insert(data_path=path, index=index, frame=float(key["frame"]))
    interp = params.get("interpolation")
    if interp:
        _set_interp(owner, interp.upper(), params.get("easing"), path)
    return {"owner": owner.name, "data_path": path, "keyframes": len(keys)}


def _set_path(owner, path: str, value) -> None:
    head, _, attr = path.rpartition(".")
    if "[" in attr:
        raise ValueError("Address array elements with `index`, not a trailing [n] in data_path")
    setattr(owner.path_resolve(head) if head else owner, attr, value)


def _set_interp(owner, interp: str, easing: str | None, path: str | None = None) -> int:
    count = 0
    for fc in iter_fcurves(owner):
        if path and fc.data_path != path:
            continue
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            if easing:
                kp.easing = easing.upper()
            count += 1
    return count


@command("set_keyframe_interpolation")
def set_keyframe_interpolation(params: dict[str, Any]):
    owner = _resolve_owner(params)
    interp = (params.get("interpolation") or "BEZIER").upper()
    count = _set_interp(owner, interp, params.get("easing"), params.get("data_path"))
    if params.get("handle_type"):
        for fc in iter_fcurves(owner):
            for kp in fc.keyframe_points:
                kp.handle_left_type = kp.handle_right_type = params["handle_type"].upper()
    return {"owner": owner.name, "interpolation": interp, "keyframes": count}


@command("make_animation_cyclic")
def make_animation_cyclic(params: dict[str, Any]):
    owner = _resolve_owner(params)
    count = 0
    for fc in iter_fcurves(owner):
        if params.get("data_path") and fc.data_path != params["data_path"]:
            continue
        if not any(m.type == "CYCLES" for m in fc.modifiers):
            fc.modifiers.new("CYCLES")
            count += 1
    return {"owner": owner.name, "cyclic_curves": count}


@command("add_fcurve_modifier")
def add_fcurve_modifier(params: dict[str, Any]):
    owner = _resolve_owner(params)
    mtype = (params.get("modifier_type") or "NOISE").upper()
    added = 0
    for fc in iter_fcurves(owner):
        if params.get("data_path") and fc.data_path != params["data_path"]:
            continue
        if params.get("index") is not None and fc.array_index != int(params["index"]):
            continue
        mod = fc.modifiers.new(mtype)
        for key, value in (params.get("settings") or {}).items():
            if hasattr(mod, key):
                setattr(mod, key, value)
        added += 1
    return {"owner": owner.name, "modifier": mtype, "curves": added}


@command("delete_keyframes")
def delete_keyframes(params: dict[str, Any]):
    owner = _resolve_owner(params)
    start = params.get("frame_start")
    end = params.get("frame_end")
    removed = 0
    for fc in list(iter_fcurves(owner)):
        if params.get("data_path") and fc.data_path != params["data_path"]:
            continue
        for kp in reversed(list(fc.keyframe_points)):
            f = kp.co.x
            if (start is None or f >= start) and (end is None or f <= end):
                fc.keyframe_points.remove(kp)
                removed += 1
    return {"owner": owner.name, "removed_keyframes": removed}


@command("move_keyframes")
def move_keyframes(params: dict[str, Any]):
    """Shift (offset) and/or retime (scale around ``pivot``) every keyframe of a target."""
    owner = _resolve_owner(params)
    offset = float(params.get("offset") or 0.0)
    scale = float(params.get("scale") or 1.0)
    pivot = float(params.get("pivot") or 0.0)
    moved = 0
    for fc in iter_fcurves(owner):
        for kp in fc.keyframe_points:
            for attr in ("co", "handle_left", "handle_right"):
                pt = getattr(kp, attr)
                pt.x = pivot + (pt.x - pivot) * scale + offset
            moved += 1
        fc.update()
    return {"owner": owner.name, "moved_keyframes": moved}


@command("list_fcurves")
def list_fcurves(params: dict[str, Any]):
    owner = _resolve_owner(params)
    return [
        {
            "data_path": fc.data_path,
            "index": fc.array_index,
            "keyframes": len(fc.keyframe_points),
            "range": list(fc.range()),
            "modifiers": [m.type for m in fc.modifiers],
            "interpolations": sorted({kp.interpolation for kp in fc.keyframe_points}),
        }
        for fc in iter_fcurves(owner)
    ]


@command("bake_animation")
def bake_animation(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    scene = bpy.context.scene
    start = int(params.get("frame_start") or scene.frame_start)
    end = int(params.get("frame_end") or scene.frame_end)
    mode = "POSE" if obj.type == "ARMATURE" and params.get("pose", True) else "OBJECT"
    with object_mode(obj, mode) as override, bpy.context.temp_override(**override):
        if mode == "POSE":
            bpy.ops.pose.select_all(action="SELECT")
        bpy.ops.nla.bake(
            frame_start=start,
            frame_end=end,
            step=int(params.get("step") or 1),
            only_selected=True,
            visual_keying=bool(params.get("visual_keying", True)),
            clear_constraints=bool(params.get("clear_constraints", False)),
            use_current_action=True,
            bake_types={mode},
        )
    return {"name": obj.name, "frame_start": start, "frame_end": end, "mode": mode}


@command("add_motion_path")
def add_motion_path(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    scene = bpy.context.scene
    viz = obj.animation_visualization.motion_path
    viz.type = "RANGE"
    viz.frame_start = int(params.get("frame_start") or scene.frame_start)
    viz.frame_end = int(params.get("frame_end") or scene.frame_end)
    with object_mode(obj) as override, bpy.context.temp_override(**override):
        bpy.ops.object.paths_calculate(start_frame=viz.frame_start, end_frame=viz.frame_end + 1)
    return {"name": obj.name, "frame_start": viz.frame_start, "frame_end": viz.frame_end}


@command("follow_path")
def follow_path(params: dict[str, Any]):
    """Animate an object along a curve (creating a circle path when none is given)."""
    import bpy

    obj = get_object(params["name"])
    if params.get("curve"):
        curve = get_object(params["curve"])
    else:
        data = bpy.data.curves.new(f"{obj.name}_Path", "CURVE")
        data.dimensions = "3D"
        spline = data.splines.new("NURBS")
        r = float(params.get("radius") or 5.0)
        pts = [
            (r * math.cos(a), r * math.sin(a), 0, 1) for a in [i * math.pi / 4 for i in range(8)]
        ]
        spline.points.add(len(pts) - 1)
        for p, co in zip(spline.points, pts, strict=True):
            p.co = co
        spline.use_cyclic_u = True
        spline.use_endpoint_u = False
        curve = bpy.data.objects.new(f"{obj.name}_Path", data)
        link_object(curve, params.get("collection"))
        curve.location = params.get("center") or (0, 0, 0)
    con = obj.constraints.new("FOLLOW_PATH")
    con.target = curve
    con.use_curve_follow = bool(params.get("follow_curve", True))
    if params.get("forward_axis"):
        con.forward_axis = params["forward_axis"].upper()
    curve.data.use_path = True
    frames = int(params.get("duration") or 120)
    start = int(params.get("frame_start") or bpy.context.scene.frame_start)
    curve.data.path_duration = frames
    con.offset_factor = 0.0
    con.use_fixed_location = True
    con.keyframe_insert("offset_factor", frame=start)
    con.offset_factor = 1.0
    con.keyframe_insert("offset_factor", frame=start + frames)
    for fc in iter_fcurves(obj):
        if "offset_factor" in fc.data_path:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
            if params.get("loop", True):
                fc.modifiers.new("CYCLES")
    return {"name": obj.name, "path": curve.name, "duration": frames}


@command("create_turntable")
def create_turntable(params: dict[str, Any]):
    """Orbit a camera 360 degrees around a target over ``frames`` frames."""
    import bpy

    target = get_object(params["target"]) if params.get("target") else None
    center = target.matrix_world.translation.copy() if target else None
    pivot = bpy.data.objects.new("Turntable_Pivot", None)
    link_object(pivot, params.get("collection"))
    if center is not None:
        pivot.location = center
    cam = bpy.data.objects.get(params.get("camera") or "") or bpy.context.scene.camera
    if cam is None:
        data = bpy.data.cameras.new("Turntable_Cam")
        cam = bpy.data.objects.new("Turntable_Cam", data)
        link_object(cam, params.get("collection"))
    dist = float(params.get("distance") or 8.0)
    height = float(params.get("height") or 2.0)
    cam.parent = pivot
    cam.location = (0, -dist, height)
    track = cam.constraints.new("TRACK_TO")
    track.target = target or pivot
    track.track_axis, track.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    bpy.context.scene.camera = cam
    start = int(params.get("frame_start") or 1)
    frames = int(params.get("frames") or 120)
    pivot.rotation_euler = (0, 0, 0)
    pivot.keyframe_insert("rotation_euler", index=2, frame=start)
    pivot.rotation_euler = (0, 0, math.tau)
    pivot.keyframe_insert("rotation_euler", index=2, frame=start + frames)
    for fc in iter_fcurves(pivot):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = start, start + frames - 1
    return {"camera": cam.name, "pivot": pivot.name, "frames": frames}


@command("create_animated_text")
def create_animated_text(params: dict[str, Any]):
    """Motion-graphics title: extruded text with a reveal/spin/bounce/fly-in animation."""
    import bpy

    body = params.get("text") or "Title"
    data = bpy.data.curves.new(params.get("name") or "AnimatedText", "FONT")
    data.body = body
    data.align_x, data.align_y = "CENTER", "CENTER"
    data.extrude = float(params.get("extrude") or 0.1)
    data.bevel_depth = float(params.get("bevel") or 0.01)
    data.size = float(params.get("size") or 1.0)
    obj = bpy.data.objects.new(data.name, data)
    link_object(obj, params.get("collection"))
    obj.location = params.get("location") or (0, 0, 0)
    obj.rotation_euler = (math.radians(90), 0, 0)
    if params.get("material"):
        mat = bpy.data.materials.get(params["material"])
        if mat:
            data.materials.append(mat)
    style = (params.get("style") or "reveal").lower()
    start = int(params.get("frame_start") or 1)
    dur = int(params.get("duration") or 40)
    end = start + dur
    if style == "reveal":
        obj.scale = (1, 1, 0.001)
        obj.keyframe_insert("scale", frame=start)
        obj.scale = (1, 1, 1)
        obj.keyframe_insert("scale", frame=end)
    elif style == "spin":
        obj.rotation_euler.z = -math.tau
        obj.keyframe_insert("rotation_euler", frame=start)
        obj.rotation_euler.z = 0
        obj.keyframe_insert("rotation_euler", frame=end)
    elif style == "scale_bounce":
        obj.scale = (0, 0, 0)
        obj.keyframe_insert("scale", frame=start)
        obj.scale = (1.15, 1.15, 1.15)
        obj.keyframe_insert("scale", frame=start + int(dur * 0.7))
        obj.scale = (1, 1, 1)
        obj.keyframe_insert("scale", frame=end)
    elif style == "fly_in":
        final = obj.location.copy()
        obj.location = (final.x, final.y - 15, final.z)
        obj.keyframe_insert("location", frame=start)
        obj.location = final
        obj.keyframe_insert("location", frame=end)
    else:
        raise ValueError("style must be reveal, spin, scale_bounce or fly_in")
    for fc in iter_fcurves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = "BACK" if style == "scale_bounce" else "EXPO"
            kp.easing = "EASE_OUT"
    return {"name": obj.name, "style": style, "frame_start": start, "frame_end": end}


@command("import_motion_capture")
def import_motion_capture(params: dict[str, Any]):
    import bpy

    path = params["path"]
    before = set(bpy.data.objects)
    if path.lower().endswith(".bvh"):
        bpy.ops.import_anim.bvh(
            filepath=path,
            global_scale=float(params.get("scale") or 1.0),
            frame_start=int(params.get("frame_start") or 1),
            use_fps_scale=bool(params.get("use_fps_scale", True)),
            update_scene_fps=bool(params.get("update_scene_fps", False)),
            update_scene_duration=bool(params.get("update_scene_duration", True)),
        )
    elif path.lower().endswith(".fbx"):
        bpy.ops.import_scene.fbx(
            filepath=path,
            global_scale=float(params.get("scale") or 1.0),
            automatic_bone_orientation=True,
        )
    else:
        raise ValueError("Motion capture import supports .bvh and .fbx")
    new = [o.name for o in set(bpy.data.objects) - before]
    return {"imported": new, "path": path}


@command("retarget_animation")
def retarget_animation(params: dict[str, Any]):
    """Drive target bones from source bones with copy-rotation constraints, optionally baked."""
    source = get_object(params["source"])
    target = get_object(params["target"])
    if source.type != "ARMATURE" or target.type != "ARMATURE":
        raise ValueError("source and target must be armatures")
    mapping = params.get("bone_map") or {
        b.name: b.name for b in source.data.bones if b.name in target.data.bones
    }
    linked = []
    for src_bone, dst_bone in mapping.items():
        pb = target.pose.bones.get(dst_bone)
        if pb is None or src_bone not in source.pose.bones:
            continue
        con = pb.constraints.new("COPY_ROTATION")
        con.name = "MCP_Retarget"
        con.target, con.subtarget = source, src_bone
        con.mix_mode = "REPLACE"
        con.target_space = con.owner_space = "LOCAL"
        linked.append(dst_bone)
    root = params.get("root_bone")
    if root and root in target.pose.bones:
        con = target.pose.bones[root].constraints.new("COPY_LOCATION")
        con.name = "MCP_Retarget"
        con.target, con.subtarget = source, mapping.get(root, root)
    if params.get("bake", True):
        bake_animation(
            {
                "name": target.name,
                "frame_start": params.get("frame_start"),
                "frame_end": params.get("frame_end"),
                "clear_constraints": False,
            }
        )
        for pb in target.pose.bones:
            for con in list(pb.constraints):
                if con.name.startswith("MCP_Retarget"):
                    pb.constraints.remove(con)
    return {
        "source": source.name,
        "target": target.name,
        "retargeted_bones": linked,
        "baked": bool(params.get("bake", True)),
    }
