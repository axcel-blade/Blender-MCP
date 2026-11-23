"""Video Sequence Editor handlers: strips, cuts, transitions, text, audio sync, output."""

from __future__ import annotations

import contextlib
from typing import Any

from ..utils.context import vse_all_strips, vse_strips
from . import command


def _editor():
    import bpy

    scene = bpy.context.scene
    return scene.sequence_editor or scene.sequence_editor_create()


def _strip(name: str):
    ed = _editor()
    strip = next((s for s in vse_all_strips(ed) if s.name == name), None)
    if strip is None:
        raise ValueError(f"Strip not found: {name}")
    return strip


def _info(s) -> dict[str, Any]:
    return {
        "name": s.name,
        "type": s.type,
        "channel": s.channel,
        "frame_start": s.frame_start,
        "frame_final_start": s.frame_final_start,
        "frame_final_end": s.frame_final_end,
        "duration": s.frame_final_duration,
        "mute": s.mute,
        "filepath": getattr(s, "filepath", None)
        or getattr(getattr(s, "sound", None), "filepath", None),
    }


def _new_effect(strips, name, etype, channel, start, end, inputs=()):
    kwargs = {"name": name, "type": etype, "channel": channel, "frame_start": start}
    for i, src in enumerate(inputs, 1):
        kwargs[f"input{i}"] = src
    attempts = [dict(kwargs, length=end - start), dict(kwargs, frame_end=end)]
    legacy = {k.replace("input", "seq"): v for k, v in kwargs.items()}
    attempts += [dict(legacy, frame_end=end)]
    last = None
    for kw in attempts:
        try:
            return strips.new_effect(**kw)
        except TypeError as exc:
            last = exc
    raise ValueError(f"Could not create {etype} strip: {last}")


@command("vse_add_strip")
def vse_add_strip(params: dict[str, Any]):
    """Add movie, sound, image or color strips. Movies optionally bring their audio."""
    ed = _editor()
    strips = vse_strips(ed)
    kind = (params.get("kind") or "movie").lower()
    channel = int(params.get("channel") or 1)
    start = int(params.get("frame_start") or 1)
    name = params.get("name") or kind.title()
    created = []
    if kind == "movie":
        s = strips.new_movie(name, params["path"], channel, start)
        created.append(s)
        if params.get("with_audio", True):
            with contextlib.suppress(Exception):  # the file has no audio stream
                created.append(
                    strips.new_sound(f"{name}_audio", params["path"], channel + 1, start)
                )
    elif kind == "sound":
        created.append(strips.new_sound(name, params["path"], channel, start))
        if params.get("volume") is not None:
            created[-1].volume = float(params["volume"])
    elif kind == "image":
        s = strips.new_image(name, params["path"], channel, start)
        length = int(params.get("length") or 100)
        s.frame_final_duration = length
        created.append(s)
    elif kind == "color":
        s = _new_effect(
            strips, name, "COLOR", channel, start, start + int(params.get("length") or 100)
        )
        s.color = (params.get("color") or (0, 0, 0))[:3]
        created.append(s)
    else:
        raise ValueError("kind must be movie, sound, image or color")
    if params.get("fit_scene_range", True):
        _fit_range()
    return {"strips": [_info(s) for s in created]}


@command("vse_add_text")
def vse_add_text(params: dict[str, Any]):
    strips = vse_strips(_editor())
    start = int(params.get("frame_start") or 1)
    end = start + int(params.get("length") or 72)
    s = _new_effect(
        strips, params.get("name") or "Text", "TEXT", int(params.get("channel") or 5), start, end
    )
    s.text = params.get("text") or "Title"
    s.font_size = float(params.get("size") or 60)
    if params.get("color"):
        s.color = (*params["color"][:3], 1.0)
    loc = params.get("location") or (0.5, 0.15)
    s.location = loc
    if params.get("shadow") is not None:
        s.use_shadow = bool(params["shadow"])
    if params.get("box") is not None and hasattr(s, "use_box"):
        s.use_box = bool(params["box"])
    for attr in ("align_x", "anchor_x"):
        if hasattr(s, attr):
            setattr(s, attr, "CENTER")
            break
    return _info(s)


@command("vse_add_transition")
def vse_add_transition(params: dict[str, Any]):
    """Cross/gamma-cross/wipe between two overlapping strips (overlap is created if needed)."""
    strips = vse_strips(_editor())
    a, b = _strip(params["strip_a"]), _strip(params["strip_b"])
    length = int(params.get("length") or 12)
    if b.frame_final_start >= a.frame_final_end:
        b.frame_start -= (b.frame_final_start - a.frame_final_end) + length
    start = int(b.frame_final_start)
    end = int(min(a.frame_final_end, start + length))
    etype = (params.get("transition") or "CROSS").upper()
    channel = max(a.channel, b.channel) + 1
    s = _new_effect(
        strips, params.get("name") or f"{etype.title()}", etype, channel, start, end, (a, b)
    )
    return _info(s)


@command("vse_add_effect")
def vse_add_effect(params: dict[str, Any]):
    """Strip effects: SPEED, GLOW, GAUSSIAN_BLUR, COLORMIX, ADJUSTMENT (TRANSFORM on older
    Blender); or modifiers (color_balance, curves, hue_correct, brightness_contrast, white_balance)
    on a strip."""
    ed = _editor()
    effect = (params.get("effect") or "ADJUSTMENT").upper()
    modifiers = {
        "COLOR_BALANCE",
        "CURVES",
        "HUE_CORRECT",
        "BRIGHT_CONTRAST",
        "WHITE_BALANCE",
        "TONEMAP",
    }
    if effect in modifiers:
        strip = _strip(params["strip"])
        mod = strip.modifiers.new(effect.title(), effect)
        for key, value in (params.get("settings") or {}).items():
            setattr(mod, key, value)
        return {"strip": strip.name, "modifier": mod.name}
    strips = vse_strips(ed)
    if effect == "ADJUSTMENT":
        start = int(params.get("frame_start") or 1)
        s = _new_effect(
            strips,
            "Adjustment",
            "ADJUSTMENT",
            int(params.get("channel") or 9),
            start,
            start + int(params.get("length") or 100),
        )
    else:
        src = _strip(params["strip"])
        s = _new_effect(
            strips,
            f"{src.name}_{effect.lower()}",
            effect,
            src.channel + 1,
            int(src.frame_final_start),
            int(src.frame_final_end),
            (src,),
        )
    for key, value in (params.get("settings") or {}).items():
        if hasattr(s, key):
            setattr(s, key, value)
    return _info(s)


@command("vse_edit_strip")
def vse_edit_strip(params: dict[str, Any]):
    """Move (frame_start/channel), trim (trim_start/trim_end in frames), mute, opacity, volume,
    speed."""
    s = _strip(params["name"])
    if params.get("frame_start") is not None:
        s.frame_start = float(params["frame_start"])
    if params.get("channel") is not None:
        s.channel = int(params["channel"])
    if params.get("trim_start") is not None:
        s.frame_offset_start = float(params["trim_start"])
    if params.get("trim_end") is not None:
        s.frame_offset_end = float(params["trim_end"])
    if params.get("mute") is not None:
        s.mute = bool(params["mute"])
    if params.get("opacity") is not None and hasattr(s, "blend_alpha"):
        s.blend_alpha = float(params["opacity"])
    if params.get("blend_type") and hasattr(s, "blend_type"):
        s.blend_type = params["blend_type"].upper()
    if params.get("volume") is not None and hasattr(s, "volume"):
        s.volume = float(params["volume"])
    if params.get("fade_in") or params.get("fade_out"):
        _fade(s, int(params.get("fade_in") or 0), int(params.get("fade_out") or 0))
    return _info(s)


def _fade(s, fade_in: int, fade_out: int) -> None:
    prop = "volume" if hasattr(s, "volume") and s.type == "SOUND" else "blend_alpha"
    full = getattr(s, prop)
    start, end = s.frame_final_start, s.frame_final_end
    if fade_in:
        setattr(s, prop, 0.0)
        s.keyframe_insert(prop, frame=start)
        setattr(s, prop, full)
        s.keyframe_insert(prop, frame=start + fade_in)
    if fade_out:
        setattr(s, prop, full)
        s.keyframe_insert(prop, frame=end - fade_out)
        setattr(s, prop, 0.0)
        s.keyframe_insert(prop, frame=end)
        setattr(s, prop, full)


@command("vse_cut_strip")
def vse_cut_strip(params: dict[str, Any]):
    """Split a movie/sound/image strip at ``frame`` into two strips (left keeps the name)."""
    s = _strip(params["name"])
    frame = int(params["frame"])
    if not (s.frame_final_start < frame < s.frame_final_end):
        raise ValueError("frame must fall inside the strip")
    strips = vse_strips(_editor())
    end_before = s.frame_final_end
    if s.type == "MOVIE":
        right = strips.new_movie(f"{s.name}_B", s.filepath, s.channel, int(s.frame_start))
    elif s.type == "SOUND":
        right = strips.new_sound(f"{s.name}_B", s.sound.filepath, s.channel, int(s.frame_start))
    else:
        raise ValueError("Only MOVIE and SOUND strips can be cut")
    right.frame_offset_start = frame - s.frame_start
    right.frame_offset_end = s.frame_offset_end
    s.frame_offset_end += end_before - frame
    return {"left": _info(s), "right": _info(right)}


@command("vse_remove_strip")
def vse_remove_strip(params: dict[str, Any]):
    if not params.get("confirmed"):
        raise PermissionError("vse_remove_strip requires confirmed=true")
    ed = _editor()
    s = _strip(params["name"])
    vse_strips(ed).remove(s)
    return {"removed": params["name"]}


@command("vse_list_strips")
def vse_list_strips(params: dict[str, Any]):
    ed = _editor()
    return sorted(
        (_info(s) for s in vse_all_strips(ed)), key=lambda i: (i["channel"], i["frame_final_start"])
    )


def _fit_range() -> None:
    import bpy

    ed = _editor()
    items = vse_all_strips(ed)
    if items:
        scene = bpy.context.scene
        scene.frame_start = int(min(s.frame_final_start for s in items))
        scene.frame_end = int(max(s.frame_final_end for s in items)) - 1


@command("vse_sync_audio")
def vse_sync_audio(params: dict[str, Any]):
    """Lock playback to audio, match scene fps to a movie strip, and fit the frame range."""
    import bpy

    scene = bpy.context.scene
    scene.sync_mode = "AUDIO_SYNC"
    if params.get("match_fps_of"):
        s = _strip(params["match_fps_of"])
        fps = getattr(s, "fps", None)
        if fps:
            scene.render.fps = round(fps)
            scene.render.fps_base = round(fps) / fps
    if params.get("align_strip") and params.get("to_frame") is not None:
        _strip(params["align_strip"]).frame_start = float(params["to_frame"])
    _fit_range()
    return {
        "sync_mode": scene.sync_mode,
        "fps": scene.render.fps / scene.render.fps_base,
        "frame_range": [scene.frame_start, scene.frame_end],
    }


@command("vse_render_video")
def vse_render_video(params: dict[str, Any]):
    import bpy

    from .render_config import set_output_format

    scene = bpy.context.scene
    path = params["path"]
    set_output_format(
        {
            "file_format": params.get("container_format") or "MP4",
            "codec": params.get("codec"),
            "audio_codec": params.get("audio_codec") or "AAC",
            "quality": params.get("quality"),
        }
    )
    scene.render.filepath = path
    scene.render.use_sequencer = True
    if params.get("resolution"):
        scene.render.resolution_x, scene.render.resolution_y = params["resolution"]
    bpy.ops.render.render(animation=True)
    return {"path": path, "frames": [scene.frame_start, scene.frame_end]}
