"""Context helpers shared by handlers: modes, overrides, version checks, safe enums."""

from __future__ import annotations

import contextlib
from typing import Any


def blender_version() -> tuple[int, int, int]:
    import bpy

    return tuple(bpy.app.version)  # type: ignore[return-value]


def require_version(minimum: tuple[int, int], feature: str) -> None:
    """Raise a readable error when the running Blender is too old for ``feature``."""
    if blender_version()[:2] < minimum:
        raise ValueError(
            f"{feature} needs Blender {minimum[0]}.{minimum[1]}+ "
            f"(running {'.'.join(map(str, blender_version()))})"
        )


def enum_items(rna_type, prop: str) -> list[str]:
    return [i.identifier for i in rna_type.bl_rna.properties[prop].enum_items]


def set_enum(owner, prop: str, value: str) -> str:
    """Assign an enum, raising a ValueError that lists the valid identifiers."""
    try:
        setattr(owner, prop, value)
    except TypeError as exc:
        valid = enum_items(type(owner), prop)
        raise ValueError(f"Invalid {prop}={value!r}; valid: {valid}") from exc
    return getattr(owner, prop)


def view3d_override() -> dict[str, Any]:
    """Return a temp_override kwargs dict pointing at a 3D viewport, or {} when headless."""
    import bpy

    wm = bpy.context.window_manager
    for window in getattr(wm, "windows", []):
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                if region is not None:
                    return {
                        "window": window,
                        "screen": window.screen,
                        "area": area,
                        "region": region,
                    }
    return {}


@contextlib.contextmanager
def object_mode(obj, mode: str = "OBJECT"):
    """Make ``obj`` active+selected, switch to ``mode``, restore the previous mode after."""
    import bpy

    view_layer = bpy.context.view_layer
    previous_active = view_layer.objects.active
    previous_mode = previous_active.mode if previous_active else "OBJECT"
    override = view3d_override()
    with bpy.context.temp_override(**override):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for other in bpy.context.selected_objects:
            other.select_set(False)
        obj.select_set(True)
        view_layer.objects.active = obj
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode=mode)
        try:
            yield override
        finally:
            if bpy.context.object and bpy.context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            if previous_active is not None and previous_mode != "OBJECT":
                with contextlib.suppress(Exception):
                    view_layer.objects.active = previous_active
                    bpy.ops.object.mode_set(mode=previous_mode)


def require_mesh(obj) -> None:
    if obj.type != "MESH":
        raise ValueError(f"{obj.name} is a {obj.type}, not a MESH")


def scene():
    import bpy

    return bpy.context.scene


def compositor_tree(create: bool = True):
    """Return the scene compositor node tree for both pre-5.0 and 5.0+ APIs."""
    import bpy

    sc = bpy.context.scene
    if hasattr(sc, "compositing_node_group"):  # Blender 5.0+
        tree = sc.compositing_node_group
        if tree is None and create:
            tree = bpy.data.node_groups.new("Compositor", "CompositorNodeTree")
            sc.compositing_node_group = tree
        return tree
    if create:
        sc.use_nodes = True
    return sc.node_tree


def vse_strips(editor):
    """Top-level strips collection (``strips`` in 4.4+, ``sequences`` before)."""
    return editor.strips if hasattr(editor, "strips") else editor.sequences


def vse_all_strips(editor):
    return list(editor.strips_all if hasattr(editor, "strips_all") else editor.sequences_all)
