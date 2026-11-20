"""Screenshot command handlers."""

from __future__ import annotations

from typing import Any

from .. import screenshots as shot
from . import command


@command("get_viewport_screenshot")
@command("capture_viewport")
@command("capture_scene_preview")
def capture_viewport(params: dict[str, Any]):
    return shot.capture_viewport(
        max_size=params.get("max_size"),
        shading=params.get("shading"),
        view=params.get("view"),
        frame=params.get("frame"),
    )


@command("capture_camera_view")
def capture_camera_view(params: dict[str, Any]):
    import bpy

    if params.get("camera"):
        from ..utils.objects import get_object

        bpy.context.scene.camera = get_object(params["camera"])
    return shot.capture_viewport(max_size=params.get("max_size"), view="CAMERA")


@command("capture_multiple_angles")
def capture_multiple_angles(params: dict[str, Any]):
    angles = params.get("angles") or ["FRONT", "RIGHT", "TOP", "PERSPECTIVE"]
    images = []
    for angle in angles:
        view = None if angle.upper() == "PERSPECTIVE" else angle
        images.append(
            {
                "angle": angle,
                **shot.capture_viewport(max_size=params.get("max_size"), view=view),
            }
        )
    return {"angles": images}


@command("capture_wireframe")
def capture_wireframe(params: dict[str, Any]):
    return shot.capture_viewport(max_size=params.get("max_size"), shading="WIREFRAME")


@command("capture_material_preview")
def capture_material_preview(params: dict[str, Any]):
    return shot.capture_viewport(max_size=params.get("max_size"), shading="MATERIAL")


@command("capture_render")
@command("inspect_render")
def capture_render(params: dict[str, Any]):
    from .rendering import get_render_result

    result = get_render_result({})
    if result.get("available") is False or not result.get("image_base64"):
        # Fall back to rendered viewport shading
        return shot.capture_viewport(max_size=params.get("max_size"), shading="RENDERED")
    return result
