"""Rendering handlers."""

from __future__ import annotations

import base64
import contextlib
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


# Scene settings a render may change; snapshotted before and restored after.
_RENDER_ATTRS = ("engine", "filepath", "resolution_percentage", "use_compositing")
_IMAGE_ATTRS = ("file_format", "color_mode", "color_depth")


def snapshot_render_settings(scene: Any) -> dict[str, Any]:
    """Record every setting a render handler may touch, so it can be put back."""
    snap: dict[str, Any] = {"camera": scene.camera, "render": {}, "image": {}, "samples": {}}
    for attr in _RENDER_ATTRS:
        if hasattr(scene.render, attr):
            snap["render"][attr] = getattr(scene.render, attr)
    image_settings = scene.render.image_settings
    for attr in _IMAGE_ATTRS:
        if hasattr(image_settings, attr):
            snap["image"][attr] = getattr(image_settings, attr)
    if hasattr(scene, "cycles") and hasattr(scene.cycles, "samples"):
        snap["samples"]["cycles"] = scene.cycles.samples
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        snap["samples"]["eevee"] = scene.eevee.taa_render_samples
    return snap


def restore_render_settings(scene: Any, snap: dict[str, Any]) -> None:
    """Put back what ``snapshot_render_settings`` recorded. Never raises."""
    # file_format first: it resets color_mode/color_depth to the format's defaults.
    for attr in _IMAGE_ATTRS:
        if attr in snap["image"]:
            with contextlib.suppress(TypeError, ValueError, AttributeError):
                setattr(scene.render.image_settings, attr, snap["image"][attr])
    for attr, value in snap["render"].items():
        with contextlib.suppress(TypeError, ValueError, AttributeError):
            setattr(scene.render, attr, value)
    if "cycles" in snap["samples"]:
        scene.cycles.samples = snap["samples"]["cycles"]
    if "eevee" in snap["samples"]:
        scene.eevee.taa_render_samples = snap["samples"]["eevee"]
    with contextlib.suppress(TypeError, ValueError, AttributeError, ReferenceError):
        scene.camera = snap["camera"]


def _set_samples(scene: Any, samples: int | None) -> None:
    if samples is None:
        return
    if hasattr(scene, "cycles") and hasattr(scene.cycles, "samples"):
        scene.cycles.samples = samples
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples


def _mtime(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def render_still(scene: Any, out: Path, *, write_still: bool = True) -> bytes:
    """Render the current frame and return the PNG bytes of *this* render.

    Raises RuntimeError instead of ever returning an older image: with
    ``write_still`` the file must be (re)written by this render; without it the
    in-memory Render Result is saved to a fresh temp file.
    """
    import tempfile

    import bpy

    before = _mtime(out)
    scene.render.filepath = str(out)
    scene.render.image_settings.file_format = "PNG"
    result = bpy.ops.render.render(write_still=write_still)
    if isinstance(result, set) and "FINISHED" not in result:
        raise RuntimeError(f"Render did not finish ({', '.join(sorted(result))}).")
    if write_still:
        after = _mtime(out)
        if after is None or after == before:
            raise RuntimeError(f"Render finished but wrote no new image to {out}.")
        return out.read_bytes()
    render_result = next(
        (img for img in bpy.data.images if getattr(img, "type", "") == "RENDER_RESULT"), None
    )
    if render_result is None:
        raise RuntimeError("Render finished but Blender has no Render Result image.")
    fd, tmp_name = tempfile.mkstemp(prefix="blender_mcp_result_", suffix=".png")
    import os

    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.unlink()
        render_result.save_render(filepath=str(tmp), scene=scene)
        if not tmp.exists():
            raise RuntimeError("Could not read the Render Result image.")
        return tmp.read_bytes()
    finally:
        tmp.unlink(missing_ok=True)


def _render(params: dict[str, Any], *, preview: bool = False, final: bool = False):
    import tempfile

    import bpy

    scene = bpy.context.scene
    snap = snapshot_render_settings(scene)
    _LAST_RENDER.clear()  # a failed render must not leave an older image behind
    try:
        if params.get("engine"):
            try:
                scene.render.engine = params["engine"]
            except TypeError as exc:
                raise ValueError(str(exc)) from exc
        samples = params.get("samples")
        if preview:
            scene.render.resolution_percentage = int(params.get("resolution_percentage") or 25)
            samples = samples or 16
        elif final:
            scene.render.resolution_percentage = int(params.get("resolution_percentage") or 100)
        elif params.get("resolution_percentage") is not None:
            scene.render.resolution_percentage = int(params["resolution_percentage"])
        samples, _, _ = _enforce_limits(samples=samples)
        _set_samples(scene, samples)

        out = params.get("output_path")
        if not out:
            out = str(Path(tempfile.gettempdir()) / "blender_mcp_render.png")
        write_still = bool(params.get("write_still", True))
        data = render_still(scene, Path(out), write_still=write_still)
        engine = scene.render.engine
    finally:
        restore_render_settings(scene, snap)

    result = {
        "output_path": out if write_still else None,
        "engine": engine,
        "preview": preview,
        "final": final,
        "image_base64": base64.b64encode(data).decode("ascii"),
        "mime_type": "image/png",
    }
    _LAST_RENDER.update(result)
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
