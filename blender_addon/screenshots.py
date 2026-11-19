"""Viewport screenshot helpers."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any


def capture_viewport(
    *,
    max_size: int | None = 1024,
    shading: str | None = None,
    view: str | None = None,
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

    out = Path(tempfile.gettempdir()) / "blender_mcp_viewport.png"
    with bpy.context.temp_override(area=area, region=region):
        bpy.ops.screen.screenshot_area(filepath=str(out))

    # restore shading
    space.shading.type = old_shading

    data = out.read_bytes() if out.exists() else b""
    # Optional downscale hint only — Blender writes full capture; clients can resize.
    result = {
        "path": str(out),
        "mime_type": "image/png",
        "image_base64": base64.b64encode(data).decode("ascii") if data else None,
        "max_size": max_size,
        "shading": shading,
        "view": view,
        "bytes": len(data),
    }
    return result


def register() -> None:
    pass


def unregister() -> None:
    pass
