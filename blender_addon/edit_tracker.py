"""Notice what the user changed by hand between AI commands.

After every bridge command the scene is snapshotted. Before the next command the
scene is compared with that snapshot: anything different was done by someone other
than the AI (the user, an undo, another add-on). The difference is reported with
the next command's reply as ``user_edits`` so the AI doesn't overwrite it.

Snapshots, not depsgraph events: Blender often fires update events for the AI's own
changes after its command has returned, which would be misattributed to the user.
All functions here must run on Blender's main thread.
"""

from __future__ import annotations

from typing import Any

MAX_OBJECTS = 5000  # skip tracking in huge scenes; snapshots would get slow
MAX_REPORTED = 40   # cap each list in a report
_PRECISION = 4

_baseline: dict[str, Any] | None = None


def _round(values: Any) -> tuple[float, ...]:
    return tuple(round(float(v), _PRECISION) for v in values)


def _object_state(obj: Any) -> dict[str, Any]:
    rotation = obj.rotation_quaternion if obj.rotation_mode == "QUATERNION" else obj.rotation_euler
    state: dict[str, Any] = {
        "type": obj.type,
        "location": _round(obj.location),
        "rotation": _round(rotation),
        "scale": _round(obj.scale),
        "parent": obj.parent.name if obj.parent else None,
        "data": obj.data.name if obj.data is not None else None,
        "hidden": bool(obj.hide_viewport) or bool(_safe(obj.hide_get, False)),
        "hide_render": bool(obj.hide_render),
        "materials": tuple(s.material.name if s.material else "" for s in obj.material_slots),
        "modifiers": tuple(m.name for m in obj.modifiers),
        "collections": tuple(sorted(c.name for c in obj.users_collection)),
    }
    data = obj.data
    if obj.type == "MESH" and data is not None:
        state["geometry"] = (len(data.vertices), len(data.edges), len(data.polygons))
    return state


def _safe(func: Any, default: Any) -> Any:
    try:
        return func()
    except Exception:  # noqa: BLE001
        return default


def snapshot() -> dict[str, Any] | None:
    """The parts of the scene a user edit is likely to touch. None if too big."""
    import bpy

    ctx = bpy.context
    scene = ctx.scene
    if scene is None or len(scene.objects) > MAX_OBJECTS:
        return None
    active = ctx.view_layer.objects.active if ctx.view_layer else None
    return {
        "scene": scene.name,
        "objects": {obj.name: _object_state(obj) for obj in scene.objects},
        "selected": sorted(o.name for o in scene.objects if _safe(o.select_get, False)),
        "active": active.name if active else None,
        "mode": ctx.mode,
        "frame": scene.frame_current,
        "materials": sorted(m.name for m in bpy.data.materials),
    }


def _capped(items: list[Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"items": items[:MAX_REPORTED]}
    if len(items) > MAX_REPORTED:
        out["more"] = len(items) - MAX_REPORTED
    return out


def diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """What changed from ``old`` to ``new``, empty when nothing did."""
    if old.get("scene") != new.get("scene"):
        return {"scene_switched": {"from": old.get("scene"), "to": new.get("scene")}}

    report: dict[str, Any] = {}
    old_objs, new_objs = old["objects"], new["objects"]
    added = sorted(set(new_objs) - set(old_objs))
    removed = sorted(set(old_objs) - set(new_objs))
    if added:
        report["added_objects"] = _capped(added)
    if removed:
        report["removed_objects"] = _capped(removed)

    changed = []
    for name in sorted(set(old_objs) & set(new_objs)):
        before, after = old_objs[name], new_objs[name]
        fields = sorted(k for k in after if before.get(k) != after.get(k))
        if fields:
            entry: dict[str, Any] = {"name": name, "changed": fields}
            for key in ("location", "rotation", "scale"):
                if key in fields:
                    entry[key] = list(after[key])
            changed.append(entry)
    if changed:
        report["changed_objects"] = _capped(changed)

    for key in ("selected", "active", "mode", "frame"):
        if old.get(key) != new.get(key):
            report[key] = new.get(key)

    new_mats = sorted(set(new["materials"]) - set(old["materials"]))
    gone_mats = sorted(set(old["materials"]) - set(new["materials"]))
    if new_mats:
        report["added_materials"] = _capped(new_mats)
    if gone_mats:
        report["removed_materials"] = _capped(gone_mats)
    return report


def collect() -> dict[str, Any]:
    """Edits made since the last command finished. Empty before the first baseline."""
    if _baseline is None:
        return {}
    current = snapshot()
    if current is None:
        return {}
    return diff(_baseline, current)


def rebaseline() -> None:
    """Remember the scene as the AI left it."""
    global _baseline
    _baseline = snapshot()


def reset() -> None:
    global _baseline
    _baseline = None
