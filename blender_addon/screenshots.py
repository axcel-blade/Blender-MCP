"""Viewport screenshot helpers."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any


def _resize_png_if_needed(path: Path, max_size: int | None) -> bytes:
    """Read PNG bytes, optionally downscaling so the longest edge <= max_size."""
    data = path.read_bytes() if path.exists() else b""
    if not data or max_size is None or max_size <= 0:
        return data

    import bpy

    img = bpy.data.images.load(filepath=str(path), check_existing=False)
    try:
        width, height = int(img.size[0]), int(img.size[1])
        longest = max(width, height)
        if longest <= max_size:
            return data

        scale = max_size / float(longest)
        new_w = max(1, int(round(width * scale)))
        new_h = max(1, int(round(height * scale)))
        img.scale(new_w, new_h)
        img.filepath_raw = str(path)
        img.file_format = "PNG"
        img.save()
        return path.read_bytes() if path.exists() else data
    finally:
        bpy.data.images.remove(img)


def capture_viewport(
    *,
    max_size: int | None = 1024,
    shading: str | None = None,
    view: str | None = None,
    frame: bool | None = None,
) -> dict[str, Any]:
    import bpy

    area = None
    region = None
    space = None
    for a in bpy.context.screen.areas:
        if a.type == "VIEW_3D":
            area = a
            for s in a.spaces:
                if s.type == "VIEW_3D":
                    space = s
                    break
            for r in a.regions:
                if r.type == "WINDOW":
                    region = r
                    break
            break
    if area is None or space is None or region is None:
        raise RuntimeError("No VIEW_3D area available for screenshot")

    old_shading = space.shading.type
    rv3d = space.region_3d
    saved_view = (
        rv3d.view_perspective,
        rv3d.view_location.copy(),
        rv3d.view_rotation.copy(),
        rv3d.view_distance,
    )
    if shading:
        shading_map = {
            "SOLID": "SOLID",
            "MATERIAL": "MATERIAL",
            "RENDERED": "RENDERED",
            "WIREFRAME": "WIREFRAME",
        }
        space.shading.type = shading_map.get(shading.upper(), shading.upper())

    if view:
        view_ops = {
            "FRONT": "VIEW_FRONT",
            "BACK": "VIEW_BACK",
            "LEFT": "VIEW_LEFT",
            "RIGHT": "VIEW_RIGHT",
            "TOP": "VIEW_TOP",
            "BOTTOM": "VIEW_BOTTOM",
            "CAMERA": "VIEW_CAMERA",
        }
        with bpy.context.temp_override(area=area, region=region):
            op = view_ops.get(view.upper())
            if op == "VIEW_CAMERA":
                bpy.ops.view3d.view_camera()
            elif op:
                bpy.ops.view3d.view_axis(type=view.upper())

    # Frame the scene when switching to an axis view (or when asked), so the model
    # doesn't get an empty or badly zoomed view.
    if frame is None:
        frame = bool(view) and view.upper() != "CAMERA"
    if frame:
        with bpy.context.temp_override(area=area, region=region):
            try:
                bpy.ops.view3d.view_all(center=False)
            except RuntimeError:
                pass

    out = Path(tempfile.gettempdir()) / "blender_mcp_viewport.png"
    method = "viewport_render"
    try:
        _render_viewport(area, region, out, max_size)
    except Exception:  # noqa: BLE001 - fall back to a raw screen grab
        method = "screenshot_area"
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.screen.screenshot_area(filepath=str(out))

    # restore the user's shading and view: looking must not move their viewport
    space.shading.type = old_shading
    (
        rv3d.view_perspective,
        rv3d.view_location,
        rv3d.view_rotation,
        rv3d.view_distance,
    ) = saved_view

    data = _resize_png_if_needed(out, max_size)
    result = {
        "path": str(out),
        "mime_type": "image/png",
        "image_base64": base64.b64encode(data).decode("ascii") if data else None,
        "max_size": max_size,
        "shading": shading,
        "view": view,
        "method": method,
        "bytes": len(data),
    }
    return result


def _render_viewport(area: Any, region: Any, out: Path, max_size: int | None) -> None:
    """Off-screen render of the 3D view: same view and shading, but no UI, popups,
    splash screen or overlapping windows in the image."""
    import bpy

    scene = bpy.context.scene
    render = scene.render
    settings = render.image_settings
    saved = (
        render.resolution_x,
        render.resolution_y,
        render.resolution_percentage,
        settings.file_format,
    )
    width, height = max(1, region.width), max(1, region.height)
    scale = 1.0
    if max_size and max_size > 0:
        scale = min(1.0, max_size / float(max(width, height)))
    try:
        render.resolution_x = max(16, int(width * scale))
        render.resolution_y = max(16, int(height * scale))
        render.resolution_percentage = 100
        settings.file_format = "PNG"
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.render.opengl(write_still=False, view_context=True)
        result = bpy.data.images.get("Render Result")
        if result is None:
            raise RuntimeError("viewport render produced no image")
        result.save_render(filepath=str(out), scene=scene)
    finally:
        (
            render.resolution_x,
            render.resolution_y,
            render.resolution_percentage,
            settings.file_format,
        ) = saved


def register() -> None:
    pass


def unregister() -> None:
    pass
