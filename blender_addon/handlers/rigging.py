"""Rigging handlers: armatures, bones, constraints, IK/FK, skinning, weights, poses, validation."""

from __future__ import annotations

from typing import Any

from ..utils.context import object_mode, require_mesh
from ..utils.objects import get_object, link_object
from . import command

# Unit-height humanoid (scaled by `height`). (name, head, tail, parent, connected)
_HUMANOID = [
    ("root", (0, 0, 0), (0, 0.15, 0), None, False),
    ("hips", (0, 0, 0.52), (0, 0, 0.58), "root", False),
    ("spine", (0, 0, 0.58), (0, 0, 0.68), "hips", True),
    ("chest", (0, 0, 0.68), (0, 0, 0.8), "spine", True),
    ("neck", (0, 0, 0.8), (0, 0, 0.87), "chest", True),
    ("head", (0, 0, 0.87), (0, 0, 1.0), "neck", True),
]
for side, sx in (("L", 1), ("R", -1)):
    _HUMANOID += [
        (f"shoulder.{side}", (0.02 * sx, 0, 0.78), (0.09 * sx, 0, 0.78), "chest", False),
        (
            f"upper_arm.{side}",
            (0.09 * sx, 0, 0.78),
            (0.24 * sx, 0.01, 0.78),
            f"shoulder.{side}",
            True,
        ),
        (
            f"forearm.{side}",
            (0.24 * sx, 0.01, 0.78),
            (0.38 * sx, 0, 0.78),
            f"upper_arm.{side}",
            True,
        ),
        (f"hand.{side}", (0.38 * sx, 0, 0.78), (0.44 * sx, 0, 0.78), f"forearm.{side}", True),
        (f"thigh.{side}", (0.06 * sx, 0, 0.52), (0.06 * sx, -0.01, 0.28), "hips", False),
        (f"shin.{side}", (0.06 * sx, -0.01, 0.28), (0.06 * sx, 0.01, 0.05), f"thigh.{side}", True),
        (f"foot.{side}", (0.06 * sx, 0.01, 0.05), (0.06 * sx, -0.08, 0.01), f"shin.{side}", True),
    ]


def _armature(name: str):
    obj = get_object(name)
    if obj.type != "ARMATURE":
        raise ValueError(f"{name} is not an ARMATURE")
    return obj


def _add_bones(obj, bones: list[dict[str, Any]], scale: float = 1.0):
    import bpy

    created = []
    with object_mode(obj, "EDIT") as override, bpy.context.temp_override(**override):
        eb = obj.data.edit_bones
        for spec in bones:
            bone = eb.get(spec["name"]) or eb.new(spec["name"])
            bone.head = [c * scale for c in spec.get("head", (0, 0, 0))]
            bone.tail = [c * scale for c in spec.get("tail", (0, 0, 1))]
            if spec.get("roll") is not None:
                bone.roll = float(spec["roll"])
            created.append(bone.name)
        for spec in bones:
            bone = eb[spec["name"]]
            if spec.get("parent"):
                parent = eb.get(spec["parent"])
                if parent is None:
                    raise ValueError(f"Parent bone not found: {spec['parent']}")
                bone.parent = parent
                bone.use_connect = bool(spec.get("connected", False))
            if "deform" in spec:
                bone.use_deform = bool(spec["deform"])
    return created


@command("create_armature")
def create_armature(params: dict[str, Any]):
    import bpy

    name = params.get("name") or "Armature"
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    link_object(obj, params.get("collection"))
    if params.get("location"):
        obj.location = params["location"]
    data.display_type = (params.get("display_type") or "OCTAHEDRAL").upper()
    obj.show_in_front = True
    template = (params.get("template") or "").lower()
    bones = list(params.get("bones") or [])
    if template == "humanoid":
        bones = [
            {"name": n, "head": h, "tail": t, "parent": p, "connected": c}
            for n, h, t, p, c in _HUMANOID
        ]
    elif template == "single" or not bones:
        bones = bones or [{"name": "Bone", "head": (0, 0, 0), "tail": (0, 0, 1)}]
    scale = float(params.get("height") or 1.0) if template == "humanoid" else 1.0
    created = _add_bones(obj, bones, scale)
    return {"name": obj.name, "bones": created}


@command("add_bones")
def add_bones(params: dict[str, Any]):
    obj = _armature(params["armature"])
    created = _add_bones(obj, params.get("bones") or [])
    return {"armature": obj.name, "bones": created}


@command("remove_bones")
def remove_bones(params: dict[str, Any]):
    import bpy

    if not params.get("confirmed"):
        raise PermissionError("remove_bones requires confirmed=true")
    obj = _armature(params["armature"])
    removed = []
    with object_mode(obj, "EDIT") as override, bpy.context.temp_override(**override):
        for name in params.get("bones") or []:
            bone = obj.data.edit_bones.get(name)
            if bone:
                obj.data.edit_bones.remove(bone)
                removed.append(name)
    return {"armature": obj.name, "removed": removed}


@command("add_bone_constraint")
def add_bone_constraint(params: dict[str, Any]):
    obj = _armature(params["armature"])
    pbone = obj.pose.bones.get(params["bone"])
    if pbone is None:
        raise ValueError(f"Bone not found: {params['bone']}")
    con = pbone.constraints.new((params.get("constraint_type") or "COPY_ROTATION").upper())
    _apply_constraint(con, params)
    return {"armature": obj.name, "bone": pbone.name, "constraint": con.name, "type": con.type}


def _apply_constraint(con, params: dict[str, Any]) -> None:
    import bpy

    if params.get("target"):
        target = bpy.data.objects.get(params["target"])
        if target is None:
            raise ValueError(f"Target not found: {params['target']}")
        con.target = target
        if params.get("subtarget") and hasattr(con, "subtarget"):
            con.subtarget = params["subtarget"]
    for key, value in (params.get("settings") or {}).items():
        if not hasattr(con, key):
            raise ValueError(f"{con.type} constraint has no setting {key!r}")
        if key in {"pole_target", "target"} and isinstance(value, str):
            value = bpy.data.objects[value]
        setattr(con, key, value)


@command("add_object_constraint")
def add_object_constraint(params: dict[str, Any]):
    obj = get_object(params["name"])
    con = obj.constraints.new((params.get("constraint_type") or "TRACK_TO").upper())
    _apply_constraint(con, params)
    return {"name": obj.name, "constraint": con.name, "type": con.type}


@command("setup_ik_chain")
def setup_ik_chain(params: dict[str, Any]):
    """Add an IK target bone (and optional pole) for ``bone`` and wire an IK constraint."""
    import bpy

    obj = _armature(params["armature"])
    bone_name = params["bone"]
    chain = int(params.get("chain_count") or 2)
    target_name = f"IK_{bone_name}"
    pole_name = f"Pole_{bone_name}" if params.get("pole", True) else None
    with object_mode(obj, "EDIT") as override, bpy.context.temp_override(**override):
        eb = obj.data.edit_bones
        src = eb.get(bone_name)
        if src is None:
            raise ValueError(f"Bone not found: {bone_name}")
        length = src.length
        tgt = eb.get(target_name) or eb.new(target_name)
        tgt.head = src.tail
        tgt.tail = src.tail + (src.tail - src.head).normalized() * length * 0.5
        tgt.parent = eb.get("root")
        tgt.use_deform = False
        if pole_name:
            mid = src.parent.head if src.parent else src.head
            pole = eb.get(pole_name) or eb.new(pole_name)
            pole.head = mid + src.z_axis * length * 2 * float(params.get("pole_direction", 1.0))
            pole.tail = pole.head + src.z_axis * length * 0.3
            pole.parent = eb.get("root")
            pole.use_deform = False
    pbone = obj.pose.bones[bone_name]
    ik = next((c for c in pbone.constraints if c.type == "IK"), None) or pbone.constraints.new("IK")
    ik.target = obj
    ik.subtarget = target_name
    ik.chain_count = chain
    if pole_name:
        ik.pole_target = obj
        ik.pole_subtarget = pole_name
        ik.pole_angle = float(params.get("pole_angle") or -1.5708)
    return {
        "armature": obj.name,
        "bone": bone_name,
        "ik_target": target_name,
        "pole": pole_name,
        "chain_count": chain,
    }


@command("create_bone_controls")
def create_bone_controls(params: dict[str, Any]):
    """Give pose bones visible custom-shape controls (circle widgets) for animators."""
    import bpy

    obj = _armature(params["armature"])
    shape = (params.get("shape") or "CIRCLE").upper()
    widget_name = f"WGT_{shape.lower()}"
    widget = bpy.data.objects.get(widget_name)
    if widget is None:
        widget = bpy.data.objects.new(widget_name, None)
        widget.empty_display_type = {"CIRCLE": "CIRCLE", "CUBE": "CUBE", "SPHERE": "SPHERE"}.get(
            shape, "CIRCLE"
        )
        link_object(widget, "Widgets")
        widget.hide_viewport = True
        widget.hide_render = True
    bones = params.get("bones") or [b.name for b in obj.pose.bones]
    done = []
    for name in bones:
        pb = obj.pose.bones.get(name)
        if pb:
            pb.custom_shape = widget
            if hasattr(pb, "custom_shape_scale_xyz"):
                pb.custom_shape_scale_xyz = [float(params.get("scale") or 1.0)] * 3
            done.append(name)
    return {"armature": obj.name, "controls": done, "widget": widget.name}


@command("bind_mesh_to_armature")
def bind_mesh_to_armature(params: dict[str, Any]):
    import bpy

    arm = _armature(params["armature"])
    meshes = [get_object(n) for n in (params.get("meshes") or [])]
    if not meshes:
        raise ValueError("meshes is required")
    mode = (params.get("mode") or "AUTO").upper()
    parent_type = {
        "AUTO": "ARMATURE_AUTO",
        "ENVELOPE": "ARMATURE_ENVELOPE",
        "EMPTY": "ARMATURE_NAME",
        "NONE": "ARMATURE",
    }[mode]
    with object_mode(arm) as override, bpy.context.temp_override(**override):
        for m in meshes:
            require_mesh(m)
            m.select_set(True)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.parent_set(type=parent_type)
    report = []
    for m in meshes:
        unweighted = sum(1 for v in m.data.vertices if not any(g.weight > 0 for g in v.groups))
        report.append(
            {
                "mesh": m.name,
                "vertex_groups": len(m.vertex_groups),
                "unweighted_vertices": unweighted,
            }
        )
    return {"armature": arm.name, "mode": mode, "meshes": report}


@command("set_vertex_weights")
def set_vertex_weights(params: dict[str, Any]):
    import mathutils

    obj = get_object(params["name"])
    require_mesh(obj)
    group = obj.vertex_groups.get(params["group"]) or obj.vertex_groups.new(name=params["group"])
    weight = float(params.get("weight", 1.0))
    mode = (params.get("mode") or "REPLACE").upper()
    indices = params.get("vertex_indices")
    if indices is None and params.get("center") is not None:
        center = obj.matrix_world.inverted() @ mathutils.Vector(params["center"])
        radius = float(params.get("radius") or 0.5)
        indices = [v.index for v in obj.data.vertices if (v.co - center).length <= radius]
    if indices is None:
        indices = [v.index for v in obj.data.vertices]
    if mode == "REMOVE":
        group.remove(indices)
    else:
        group.add(indices, weight, mode)
    return {"name": obj.name, "group": group.name, "vertices": len(indices), "mode": mode}


@command("normalize_vertex_weights")
def normalize_vertex_weights(params: dict[str, Any]):
    obj = get_object(params["name"])
    require_mesh(obj)
    locked = {g.index for g in obj.vertex_groups if g.lock_weight}
    fixed = 0
    for v in obj.data.vertices:
        groups = [g for g in v.groups if g.group not in locked]
        total = sum(g.weight for g in groups)
        if total > 0 and abs(total - 1.0) > 1e-4:
            for g in groups:
                g.weight /= total
            fixed += 1
    return {"name": obj.name, "normalized_vertices": fixed}


@command("set_bone_pose")
def set_bone_pose(params: dict[str, Any]):
    obj = _armature(params["armature"])
    results = []
    for spec in params.get("poses") or []:
        pb = obj.pose.bones.get(spec["bone"])
        if pb is None:
            raise ValueError(f"Bone not found: {spec['bone']}")
        if spec.get("rotation_euler") is not None:
            pb.rotation_mode = spec.get("rotation_mode", "XYZ")
            pb.rotation_euler = spec["rotation_euler"]
        if spec.get("rotation_quaternion") is not None:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = spec["rotation_quaternion"]
        if spec.get("location") is not None:
            pb.location = spec["location"]
        if spec.get("scale") is not None:
            pb.scale = spec["scale"]
        frame = spec.get("frame", params.get("frame"))
        if frame is not None:
            rot = "rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler"
            for path in ("location", rot, "scale"):
                pb.keyframe_insert(path, frame=int(frame), group=pb.name)
        results.append(pb.name)
    return {"armature": obj.name, "posed": results}


@command("reset_pose")
def reset_pose(params: dict[str, Any]):
    obj = _armature(params["armature"])
    for pb in obj.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    return {"armature": obj.name, "reset": len(obj.pose.bones)}


@command("create_walk_cycle")
def create_walk_cycle(params: dict[str, Any]):
    """Keyframe a looping walk on a humanoid template rig (thigh/shin/upper_arm bones)."""
    import math

    obj = _armature(params["armature"])
    start = int(params.get("frame_start") or 1)
    length = int(params.get("cycle_frames") or 24)
    swing = math.radians(float(params.get("stride_angle") or 30.0))
    keys = [0, length // 4, length // 2, 3 * length // 4, length]
    phases = [0, 1, 0, -1, 0]
    missing = [b for b in ("thigh.L", "thigh.R", "shin.L", "shin.R") if b not in obj.pose.bones]
    if missing:
        raise ValueError(f"Rig lacks bones {missing}; create it with template='humanoid'")
    for k, ph in zip(keys, phases, strict=True):
        f = start + k
        for side, sign in (("L", 1), ("R", -1)):
            thigh, shin = obj.pose.bones[f"thigh.{side}"], obj.pose.bones[f"shin.{side}"]
            thigh.rotation_mode = shin.rotation_mode = "XYZ"
            thigh.rotation_euler = (swing * ph * sign, 0, 0)
            # Knee bends most while the leg swings back, a little at the passing pose.
            shin.rotation_euler = (-swing * (0.8 if ph * sign < 0 else 0.2), 0, 0)
            thigh.keyframe_insert("rotation_euler", frame=f)
            shin.keyframe_insert("rotation_euler", frame=f)
            arm = obj.pose.bones.get(f"upper_arm.{side}")
            if arm:
                arm.rotation_mode = "XYZ"
                arm.rotation_euler = (-swing * 0.6 * ph * sign, 0, 0)
                arm.keyframe_insert("rotation_euler", frame=f)
        hips = obj.pose.bones.get("hips")
        if hips:
            hips.location = (0, 0, -0.02 if ph else 0.0)
            hips.keyframe_insert("location", frame=f)
    from .animation_advanced import iter_fcurves

    for fc in iter_fcurves(obj):
        if not any(m.type == "CYCLES" for m in fc.modifiers):
            fc.modifiers.new("CYCLES")
    return {"armature": obj.name, "frame_start": start, "cycle_frames": length, "looping": True}


@command("validate_rig")
def validate_rig(params: dict[str, Any]):
    import bpy

    obj = _armature(params["armature"])
    issues = []
    bones = obj.data.bones
    if not bones:
        issues.append("Armature has no bones")
    roots = [b.name for b in bones if b.parent is None]
    if len(roots) > 1:
        issues.append(f"Multiple root bones: {roots}")
    if any(abs(s - 1.0) > 1e-4 for s in obj.scale):
        issues.append("Armature object has unapplied scale")
    zero = [b.name for b in bones if b.length < 1e-4]
    if zero:
        issues.append(f"Zero-length bones: {zero}")
    deform = {b.name for b in bones if b.use_deform}
    skinned = [
        o
        for o in bpy.data.objects
        if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == obj for m in o.modifiers)
    ]
    for mesh in skinned:
        groups = {g.name for g in mesh.vertex_groups}
        missing = sorted(deform - groups)
        if missing:
            issues.append(f"{mesh.name}: no vertex group for deform bones {missing[:10]}")
        unweighted = sum(1 for v in mesh.data.vertices if not any(g.weight > 0 for g in v.groups))
        if unweighted:
            issues.append(f"{mesh.name}: {unweighted} vertices have no weights")
    for pb in obj.pose.bones:
        for con in pb.constraints:
            if hasattr(con, "target") and con.target is None:
                issues.append(f"{pb.name}: constraint {con.name} has no target")
            if not con.is_valid:
                issues.append(f"{pb.name}: constraint {con.name} is invalid")
    return {
        "armature": obj.name,
        "bones": len(bones),
        "deform_bones": len(deform),
        "skinned_meshes": [m.name for m in skinned],
        "issues": issues,
        "valid": not issues,
    }


@command("test_rig_deformation")
def test_rig_deformation(params: dict[str, Any]):
    """Rotate each deform bone briefly and report meshes whose vertices do not move."""
    import bpy

    obj = _armature(params["armature"])
    skinned = [
        o
        for o in bpy.data.objects
        if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == obj for m in o.modifiers)
    ]
    dead = []
    for pb in obj.pose.bones:
        if not pb.bone.use_deform:
            continue
        saved_mode, saved = pb.rotation_mode, tuple(pb.rotation_euler)
        moved = False
        before = {}
        dg = bpy.context.evaluated_depsgraph_get()
        for m in skinned:
            before[m.name] = [v.co.copy() for v in m.evaluated_get(dg).data.vertices]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.5, 0, 0)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        for m in skinned:
            after = m.evaluated_get(dg).data.vertices
            if any((a.co - b).length > 1e-5 for a, b in zip(after, before[m.name], strict=False)):
                moved = True
                break
        pb.rotation_euler = saved
        pb.rotation_mode = saved_mode
        if not moved:
            dead.append(pb.name)
    bpy.context.view_layer.update()
    return {"armature": obj.name, "bones_without_effect": dead, "ok": not dead}


@command("get_rig_info")
def get_rig_info(params: dict[str, Any]):
    obj = _armature(params["armature"])
    return {
        "name": obj.name,
        "pose_position": obj.data.pose_position,
        "bones": [
            {
                "name": b.name,
                "parent": b.parent.name if b.parent else None,
                "head": list(b.head_local),
                "tail": list(b.tail_local),
                "deform": b.use_deform,
                "constraints": [c.type for c in obj.pose.bones[b.name].constraints],
            }
            for b in obj.data.bones
        ],
    }
