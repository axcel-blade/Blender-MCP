"""Rendering handlers."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from . import command

_LAST_RENDER: dict[str, Any] = {}


def _prefs():
    from ..utils.prefs import get_preferences

    return get_preferences()


def _enforce_limits(samples=None, res_x=None, res_y=None):
    prefs = _prefs()
    max_samples = getattr(prefs, "render_max_samples", 128) if prefs else 128
    max_res = getattr(prefs, "render_max_resolution", 1920) if prefs else 1920
    if samples is not None and samples > max_samples:
        samples = max_samples
    if res_x is not None and res_x > max_res:
        res_x = max_res
    if res_y is not None and res_y > max_res:
        res_y = max_res
    return samples, res_x, res_y


@command("get_render_settings")
def get_render_settings(params: dict[str, Any]):
    from .scene import get_render_settings as _grs

    return _grs(params)


@command("set_render_settings")
def set_render_settings(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    settings = params.get("settings") or {}
    if "engine" in settings:
        try:
            scene.render.engine = settings["engine"]
        except TypeError as exc:
            raise ValueError(f"Invalid engine: {exc}") from exc
    if "resolution_x" in settings or "resolution_y" in settings:
        _, rx, ry = _enforce_limits(
            res_x=settings.get("resolution_x", scene.render.resolution_x),
            res_y=settings.get("resolution_y", scene.render.resolution_y),
        )
        scene.render.resolution_x = int(rx)
        scene.render.resolution_y = int(ry)
    if "resolution_percentage" in settings:
        scene.render.resolution_percentage = int(settings["resolution_percentage"])
    if "film_transparent" in settings:
        scene.render.film_transparent = bool(settings["film_transparent"])
    if "filepath" in settings:
        scene.render.filepath = settings["filepath"]
    if "samples" in settings:
        samples, _, _ = _enforce_limits(samples=int(settings["samples"]))
        if hasattr(scene, "cycles"):
            scene.cycles.samples = samples
        if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = samples
    return get_render_settings({})


@command("set_output_path")
def set_output_path(params: dict[str, Any]):
    import bpy

    bpy.context.scene.render.filepath = params["path"]
    return {"filepath": bpy.context.scene.render.filepath}


def _render(params: dict[str, Any], *, preview: bool = False, final: bool = False):
    import tempfile

    import bpy

    scene = bpy.context.scene
    if params.get("engine"):
        try:
            scene.render.engine = params["engine"]
        except TypeError as exc:
            raise ValueError(str(exc)) from exc

    old = {
        "percentage": scene.render.resolution_percentage,
        "filepath": scene.render.filepath,
    }
    samples = params.get("samples")
    if preview:
        scene.render.resolution_percentage = int(params.get("resolution_percentage") or 25)
        samples = samples or 16
    elif final:
        scene.render.resolution_percentage = int(params.get("resolution_percentage") or 100)
    else:
        if params.get("resolution_percentage") is not None:
            scene.render.resolution_percentage = int(params["resolution_percentage"])

    samples, _, _ = _enforce_limits(samples=samples)
    if samples is not None:
        if hasattr(scene, "cycles"):
            scene.cycles.samples = samples
        if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = samples

    out = params.get("output_path")
    if not out:
        out = str(Path(tempfile.gettempdir()) / "blender_mcp_render.png")
    scene.render.filepath = out
    scene.render.image_settings.file_format = "PNG"

    bpy.ops.render.render(write_still=bool(params.get("write_still", True)))

    image_b64 = None
    if Path(out).exists():
        image_b64 = base64.b64encode(Path(out).read_bytes()).decode("ascii")

    # restore percentage/path preferences lightly
    scene.render.resolution_percentage = old["percentage"]

    result = {
        "output_path": out,
        "engine": scene.render.engine,
        "preview": preview,
        "final": final,
        "image_base64": image_b64,
        "mime_type": "image/png",
    }
    _LAST_RENDER.clear()
    _LAST_RENDER.update(result)
    # Avoid returning huge payloads twice in history consumers — still return once
    return result


@command("render_scene")
def render_scene(params: dict[str, Any]):
    return _render(params)


@command("render_preview")
def render_preview(params: dict[str, Any]):
    return _render(params, preview=True)


@command("render_final")
def render_final(params: dict[str, Any]):
    return _render(params, final=True)


@command("render_animation")
def render_animation(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    if params.get("frame_start") is not None:
        scene.frame_start = int(params["frame_start"])
    if params.get("frame_end") is not None:
        scene.frame_end = int(params["frame_end"])
    if params.get("output_path"):
        scene.render.filepath = params["output_path"]
    bpy.ops.render.render(animation=True)
    return {
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "filepath": scene.render.filepath,
    }


@command("get_render_result")
def get_render_result(params: dict[str, Any]):
    if not _LAST_RENDER:
        return {"available": False}
    data = dict(_LAST_RENDER)
    return data
