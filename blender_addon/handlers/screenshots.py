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


def _resolve_camera(name: str | None):
    import bpy

    scene = bpy.context.scene
    if name:
        from ..utils.objects import get_object

        cam = get_object(name)
        if cam.type != "CAMERA":
            raise ValueError(f"'{name}' is a {cam.type} object, not a camera.")
        return cam
    if scene.camera is None:
        raise ValueError(
            "The scene has no active camera. Add one (bpy.ops.object.camera_add) and set "
            "scene.camera, or pass camera=<name>."
        )
    return scene.camera


@command("capture_camera_view")
def capture_camera_view(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    previous = scene.camera
    cam = _resolve_camera(params.get("camera"))
    scene.camera = cam
    try:
        return shot.capture_viewport(max_size=params.get("max_size"), view="CAMERA")
    finally:
        scene.camera = previous


@command("capture_render_view")
def capture_render_view(params: dict[str, Any]):
    """Render the frame from a camera (compositor on), downscaled, settings restored."""
    import base64
    import os
    import tempfile
    import time
    from pathlib import Path

    import bpy

    from .rendering import (
        _enforce_limits,
        _set_samples,
        render_still,
        restore_render_settings,
        snapshot_render_settings,
    )

    scene = bpy.context.scene
    cam = _resolve_camera(params.get("camera"))
    max_size = max(16, int(params.get("max_size") or 768))
    # Addon preference limits apply on top of the server's own limits.
    _, lim_x, lim_y = _enforce_limits(res_x=max_size, res_y=max_size)
    target = min(max_size, int(lim_x), int(lim_y))
    if params.get("max_resolution"):
        target = min(target, int(params["max_resolution"]))

    snap = snapshot_render_settings(scene)
    fd, name = tempfile.mkstemp(prefix="blender_mcp_look_", suffix=".png")
    os.close(fd)
    out = Path(name)
    out.unlink()  # render_still requires the file to be freshly written
    started = time.monotonic()
    try:
        scene.camera = cam
        rx, ry = scene.render.resolution_x, scene.render.resolution_y
        pct = int(100 * target / float(max(rx, ry, 1)))
        scene.render.resolution_percentage = max(1, min(100, pct))
        # The sample count of the engine that will actually render.
        engine_key = "cycles" if scene.render.engine == "CYCLES" else "eevee"
        current = snap["samples"].get(engine_key)
        samples, _, _ = _enforce_limits(samples=params.get("samples") or current)
        if samples is not None and params.get("max_samples"):
            samples = min(int(samples), int(params["max_samples"]))
        _set_samples(scene, samples)
        if hasattr(scene.render, "use_compositing"):
            scene.render.use_compositing = True
        render_still(scene, out, write_still=True)
        engine = scene.render.engine
        width = int(rx * scene.render.resolution_percentage / 100)
        height = int(ry * scene.render.resolution_percentage / 100)
        data = shot._resize_png_if_needed(out, max_size)
    finally:
        restore_render_settings(scene, snap)
        out.unlink(missing_ok=True)
    if not data:
        raise RuntimeError("Render produced an empty image.")
    return {
        "camera": cam.name,
        "engine": engine,
        "samples": samples,
        "resolution": [width, height],
        "compositor": True,
        "render_seconds": round(time.monotonic() - started, 2),
        "image_base64": base64.b64encode(data).decode("ascii"),
        "mime_type": "image/png",
    }


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
