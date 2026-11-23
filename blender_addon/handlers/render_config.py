"""Render engine configuration, passes, color management, output formats, batch rendering,
render optimization, plus lighting/camera cinematography helpers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..utils.context import enum_items, set_enum
from ..utils.objects import get_object, link_object
from . import command


def _engine_id(name: str) -> str:
    import bpy

    valid = enum_items(bpy.types.RenderSettings, "engine")
    name = name.upper()
    if name in valid:
        return name
    aliases = {"EEVEE": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"], "WORKBENCH": ["BLENDER_WORKBENCH"]}
    for candidate in aliases.get(name, []):
        if candidate in valid:
            return candidate
    raise ValueError(f"Unknown engine {name!r}; valid: {valid}")


@command("configure_cycles")
def configure_cycles(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    c = scene.cycles
    if params.get("samples") is not None:
        c.samples = int(params["samples"])
    if params.get("preview_samples") is not None:
        c.preview_samples = int(params["preview_samples"])
    if params.get("adaptive_threshold") is not None:
        c.use_adaptive_sampling = True
        c.adaptive_threshold = float(params["adaptive_threshold"])
    if params.get("denoise") is not None:
        c.use_denoising = bool(params["denoise"])
    if params.get("denoiser"):
        set_enum(c, "denoiser", params["denoiser"].upper())
    if params.get("max_bounces") is not None:
        c.max_bounces = int(params["max_bounces"])
    if params.get("time_limit") is not None:
        c.time_limit = float(params["time_limit"])
    device_report = None
    if params.get("device"):
        device = params["device"].upper()
        c.device = "GPU" if device == "GPU" else "CPU"
        if device == "GPU":
            device_report = _enable_gpu(params.get("compute_type"))
    for key, value in (params.get("settings") or {}).items():
        if not hasattr(c, key):
            raise ValueError(f"Cycles has no setting {key!r}")
        setattr(c, key, value)
    return {
        "engine": "CYCLES",
        "samples": c.samples,
        "device": c.device,
        "denoise": c.use_denoising,
        "gpu": device_report,
    }


def _enable_gpu(compute_type: str | None):
    import bpy

    addon = bpy.context.preferences.addons.get("cycles")
    if addon is None:
        return {"error": "Cycles add-on preferences unavailable"}
    prefs = addon.preferences
    order = [compute_type.upper()] if compute_type else ["OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"]
    chosen = None
    for ctype in order:
        try:
            prefs.compute_device_type = ctype
        except TypeError:
            continue
        prefs.refresh_devices() if hasattr(prefs, "refresh_devices") else prefs.get_devices()
        devices = [d for d in prefs.devices if d.type == ctype]
        if devices:
            for d in prefs.devices:
                d.use = d.type == ctype
            chosen = {"compute_device_type": ctype, "devices": [d.name for d in devices]}
            break
    if chosen is None:
        bpy.context.scene.cycles.device = "CPU"
        return {"warning": "No GPU compute device found; using CPU"}
    return chosen


@command("configure_eevee")
def configure_eevee(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    scene.render.engine = _engine_id("EEVEE")
    e = scene.eevee
    if params.get("samples") is not None:
        e.taa_render_samples = int(params["samples"])
    if params.get("raytracing") is not None and hasattr(e, "use_raytracing"):
        e.use_raytracing = bool(params["raytracing"])
    if params.get("shadows") is not None and hasattr(e, "use_shadows"):
        e.use_shadows = bool(params["shadows"])
    if params.get("volumetrics_resolution") and hasattr(e, "volumetric_tile_size"):
        e.volumetric_tile_size = str(params["volumetrics_resolution"])
    for key, value in (params.get("settings") or {}).items():
        if not hasattr(e, key):
            raise ValueError(f"EEVEE has no setting {key!r}")
        setattr(e, key, value)
    return {"engine": scene.render.engine, "samples": e.taa_render_samples}


@command("configure_workbench")
def configure_workbench(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    if params.get("lighting"):
        shading.light = params["lighting"].upper()
    if params.get("color_type"):
        shading.color_type = params["color_type"].upper()
    if params.get("show_cavity") is not None:
        shading.show_cavity = bool(params["show_cavity"])
    if params.get("show_outline") is not None:
        shading.show_object_outline = bool(params["show_outline"])
    return {"engine": "BLENDER_WORKBENCH", "light": shading.light, "color_type": shading.color_type}


_PASSES = {
    "z": "use_pass_z",
    "depth": "use_pass_z",
    "mist": "use_pass_mist",
    "normal": "use_pass_normal",
    "vector": "use_pass_vector",
    "uv": "use_pass_uv",
    "object_index": "use_pass_object_index",
    "material_index": "use_pass_material_index",
    "diffuse_color": "use_pass_diffuse_color",
    "diffuse_direct": "use_pass_diffuse_direct",
    "glossy_direct": "use_pass_glossy_direct",
    "emission": "use_pass_emit",
    "environment": "use_pass_environment",
    "ao": "use_pass_ambient_occlusion",
    "shadow": "use_pass_shadow",
    "cryptomatte_object": "use_pass_cryptomatte_object",
    "cryptomatte_material": "use_pass_cryptomatte_material",
}


@command("configure_render_passes")
def configure_render_passes(params: dict[str, Any]):
    import bpy

    layer = bpy.context.view_layer
    enabled, unsupported = [], []
    for name in params.get("passes") or []:
        attr = _PASSES.get(name.lower())
        owner = layer
        if attr is None or not hasattr(owner, attr):
            if hasattr(layer, "cycles") and hasattr(layer.cycles, f"use_pass_{name.lower()}"):
                owner, attr = layer.cycles, f"use_pass_{name.lower()}"
            else:
                unsupported.append(name)
                continue
        setattr(owner, attr, bool(params.get("enable", True)))
        enabled.append(name)
    return {
        "view_layer": layer.name,
        "passes": enabled,
        "unsupported": unsupported,
        "known_passes": sorted(_PASSES),
    }


@command("set_color_management")
def set_color_management(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    vs = scene.view_settings
    if params.get("view_transform"):
        set_enum(vs, "view_transform", params["view_transform"])
    if params.get("look"):
        set_enum(vs, "look", params["look"])
    if params.get("exposure") is not None:
        vs.exposure = float(params["exposure"])
    if params.get("gamma") is not None:
        vs.gamma = float(params["gamma"])
    if params.get("display_device"):
        set_enum(scene.display_settings, "display_device", params["display_device"])
    return {
        "view_transform": vs.view_transform,
        "look": vs.look,
        "exposure": vs.exposure,
        "gamma": vs.gamma,
    }


@command("set_output_format")
def set_output_format(params: dict[str, Any]):
    import bpy

    r = bpy.context.scene.render
    fmt = (params.get("file_format") or "PNG").upper()
    img = r.image_settings
    if fmt in {"FFMPEG", "MP4", "MOV", "MKV", "WEBM"}:
        if hasattr(img, "media_type"):  # Blender 5.0+
            img.media_type = "VIDEO"
        else:
            img.file_format = "FFMPEG"
        container = {"MP4": "MPEG4", "MOV": "QUICKTIME", "MKV": "MKV", "WEBM": "WEBM"}.get(
            fmt, "MPEG4"
        )
        set_enum(r.ffmpeg, "format", params.get("container") or container)
        set_enum(
            r.ffmpeg, "codec", params.get("codec") or ("WEBM" if container == "WEBM" else "H264")
        )
        if params.get("quality"):
            set_enum(r.ffmpeg, "constant_rate_factor", params["quality"].upper())
        if params.get("audio_codec") is not None:
            set_enum(r.ffmpeg, "audio_codec", params["audio_codec"].upper())
    else:
        if hasattr(img, "media_type"):
            img.media_type = "MULTI_LAYER_IMAGE" if fmt == "OPEN_EXR_MULTILAYER" else "IMAGE"
        set_enum(img, "file_format", fmt)
        if params.get("color_depth"):
            set_enum(img, "color_depth", str(params["color_depth"]))
        if params.get("color_mode"):
            set_enum(img, "color_mode", params["color_mode"].upper())
        if params.get("compression") is not None and hasattr(img, "compression"):
            img.compression = int(params["compression"])
    if params.get("film_transparent") is not None:
        r.film_transparent = bool(params["film_transparent"])
    return {
        "file_format": img.file_format,
        "ffmpeg_format": r.ffmpeg.format
        if fmt in {"FFMPEG", "MP4", "MOV", "MKV", "WEBM"}
        else None,
    }


@command("optimize_render_settings")
def optimize_render_settings(params: dict[str, Any]):
    """Apply a quality/speed profile: draft, preview, balanced, final, cinematic."""
    import bpy

    profile = (params.get("profile") or "balanced").lower()
    table = {
        "draft": (32, 50, 4, 0.1),
        "preview": (64, 75, 6, 0.05),
        "balanced": (256, 100, 8, 0.02),
        "final": (1024, 100, 12, 0.01),
        "cinematic": (2048, 100, 16, 0.005),
    }
    if profile not in table:
        raise ValueError(f"profile must be one of {list(table)}")
    samples, pct, bounces, threshold = table[profile]
    scene = bpy.context.scene
    r = scene.render
    r.resolution_percentage = pct
    changes = {"resolution_percentage": pct}
    if r.engine == "CYCLES":
        c = scene.cycles
        c.samples, c.max_bounces = samples, bounces
        c.use_adaptive_sampling, c.adaptive_threshold = True, threshold
        c.use_denoising = True
        c.diffuse_bounces = min(bounces // 2, 6)
        c.glossy_bounces = min(bounces // 2, 6)
        c.transparent_max_bounces = bounces
        c.caustics_reflective = c.caustics_refractive = profile in {"final", "cinematic"}
        if hasattr(c, "use_light_tree"):
            c.use_light_tree = True
        r.use_persistent_data = True
        changes.update(
            {"samples": samples, "max_bounces": bounces, "adaptive_threshold": threshold}
        )
    else:
        scene.eevee.taa_render_samples = max(16, samples // 8)
        changes["eevee_samples"] = scene.eevee.taa_render_samples
    heavy = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in scene.objects:
        if o.type == "MESH" and not o.hide_render:
            n = len(o.evaluated_get(dg).data.polygons)
            if n > 500_000:
                heavy.append({"name": o.name, "polygons": n})
    return {
        "profile": profile,
        "engine": r.engine,
        "changes": changes,
        "heavy_objects": heavy,
        "tip": "Use decimate_mesh or instancing on heavy_objects" if heavy else None,
    }


@command("batch_render")
def batch_render(params: dict[str, Any]):
    """Render a still per camera (and optionally a frame list) into ``output_dir``."""
    import bpy

    scene = bpy.context.scene
    out_dir = Path(params["output_dir"]).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    cams = params.get("cameras") or [o.name for o in scene.objects if o.type == "CAMERA"]
    frames = params.get("frames") or [scene.frame_current]
    original = (scene.camera, scene.frame_current, scene.render.filepath)
    rendered = []
    try:
        for cam_name in cams:
            scene.camera = get_object(cam_name)
            for f in frames:
                scene.frame_set(int(f))
                path = out_dir / f"{cam_name}_{int(f):04d}{scene.render.file_extension}"
                if path.exists() and not params.get("overwrite", False):
                    rendered.append({"camera": cam_name, "frame": f, "skipped": "exists"})
                    continue
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                rendered.append({"camera": cam_name, "frame": f, "path": str(path)})
    finally:
        scene.camera, scene.render.filepath = original[0], original[2]
        scene.frame_set(original[1])
    return {"renders": rendered, "count": len(rendered)}


# ---------------------------------------------------------------- lighting helpers


def kelvin_to_rgb(kelvin: float) -> tuple[float, float, float]:
    """Tanner Helland approximation, returned in 0..1 linear-ish RGB."""
    t = max(1000.0, min(40000.0, kelvin)) / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = (
        (99.4708025861 * math.log(t) - 161.1195681661)
        if t <= 66
        else 288.1221695283 * ((t - 60) ** -0.0755148492)
    )
    b = (
        255.0
        if t >= 66
        else (0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    )
    return tuple(max(0.0, min(255.0, c)) / 255.0 for c in (r, g, b))  # type: ignore[return-value]


@command("set_light_properties")
def set_light_properties(params: dict[str, Any]):
    obj = get_object(params["name"])
    if obj.type != "LIGHT":
        raise ValueError("Not a light")
    light = obj.data
    if params.get("energy") is not None:
        light.energy = float(params["energy"])
    if params.get("color") is not None:
        light.color = params["color"][:3]
    if params.get("temperature") is not None:
        kelvin = float(params["temperature"])
        if hasattr(light, "use_temperature"):  # Blender 5.0+
            light.use_temperature = True
            light.temperature = kelvin
        else:
            light.color = kelvin_to_rgb(kelvin)
    if params.get("size") is not None:
        if light.type == "AREA":
            light.size = float(params["size"])
        elif light.type == "SUN":
            light.angle = math.radians(float(params["size"]))
        else:
            light.shadow_soft_size = float(params["size"])
    if params.get("cast_shadows") is not None:
        light.use_shadow = bool(params["cast_shadows"])
    if params.get("spot_angle") is not None and light.type == "SPOT":
        light.spot_size = math.radians(float(params["spot_angle"]))
    if params.get("spot_blend") is not None and light.type == "SPOT":
        light.spot_blend = float(params["spot_blend"])
    if params.get("area_shape") and light.type == "AREA":
        light.shape = params["area_shape"].upper()
    return {
        "name": obj.name,
        "type": light.type,
        "energy": light.energy,
        "color": list(light.color),
        "shadows": light.use_shadow,
    }


@command("create_studio_lighting")
def create_studio_lighting(params: dict[str, Any]):
    """Studio/cinematic rigs aimed at a target: three_point, softbox, rembrandt, rim,
    high_key, low_key, product, noir, golden_hour."""
    import bpy
    import mathutils

    style = (params.get("style") or "three_point").lower()
    target = get_object(params["target"]) if params.get("target") else None
    center = target.matrix_world.translation.copy() if target else mathutils.Vector()
    size = max(target.dimensions) if target else 2.0
    d = max(size * 2.5, 3.0) * float(params.get("distance_scale") or 1.0)
    coll = params.get("collection") or f"Lighting_{style}"
    rigs = {
        "three_point": [
            ("Key", "AREA", (1, -1, 0.8), 1000, 4500, 1.0),
            ("Fill", "AREA", (-1.2, -0.8, 0.4), 300, 6000, 1.5),
            ("Rim", "AREA", (0.2, 1.3, 1.0), 700, 6500, 0.5),
        ],
        "softbox": [
            ("Softbox_L", "AREA", (-1, -1, 0.6), 800, 5500, 2.0),
            ("Softbox_R", "AREA", (1, -1, 0.6), 800, 5500, 2.0),
            ("Top", "AREA", (0, 0, 1.5), 400, 5500, 2.5),
        ],
        "rembrandt": [
            ("Key", "SPOT", (1.1, -0.6, 1.0), 1500, 3800, 0.3),
            ("Fill", "AREA", (-1.2, -1, 0.3), 80, 5000, 1.5),
        ],
        "rim": [
            ("Rim_L", "AREA", (-1, 1, 0.6), 900, 7000, 0.4),
            ("Rim_R", "AREA", (1, 1, 0.6), 900, 7000, 0.4),
        ],
        "high_key": [
            ("Key", "AREA", (0.8, -1, 0.8), 900, 6000, 3.0),
            ("Fill", "AREA", (-0.8, -1, 0.6), 700, 6000, 3.0),
            ("Back", "AREA", (0, 1.2, 0.8), 600, 6500, 3.0),
        ],
        "low_key": [("Key", "SPOT", (1.3, -0.4, 1.2), 1200, 4200, 0.2)],
        "product": [
            ("Key", "AREA", (1, -1, 1), 700, 5600, 1.5),
            ("Fill", "AREA", (-1, -0.8, 0.5), 250, 5600, 2.0),
            ("Top", "AREA", (0, 0, 1.6), 350, 6000, 2.0),
            ("Kicker", "AREA", (0, 1.3, 0.3), 400, 7000, 0.6),
        ],
        "noir": [("Key", "SPOT", (-1.2, -0.3, 1.3), 2000, 3400, 0.1)],
        "golden_hour": [
            ("Sun", "SUN", (1.5, -1, 0.25), 4, 3200, 2.0),
            ("Sky_Fill", "AREA", (-1, -1, 1), 150, 9000, 3.0),
        ],
    }
    if style not in rigs:
        raise ValueError(f"style must be one of {sorted(rigs)}")
    created = []
    for name, ltype, direction, energy, kelvin, size_factor in rigs[style]:
        light = bpy.data.lights.new(f"{style}_{name}", ltype)
        light.energy = energy * (1 if ltype == "SUN" else (d / 4) ** 2)
        if hasattr(light, "use_temperature"):
            light.use_temperature, light.temperature = True, kelvin
        else:
            light.color = kelvin_to_rgb(kelvin)
        if ltype == "AREA":
            light.size = size * size_factor
        elif ltype == "SPOT":
            light.spot_size, light.spot_blend = math.radians(45), 0.4
        obj = bpy.data.objects.new(light.name, light)
        link_object(obj, coll)
        obj.location = center + mathutils.Vector(direction).normalized() * d
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
        created.append(obj.name)
    return {"style": style, "lights": created, "collection": coll}


@command("analyze_lighting")
def analyze_lighting(params: dict[str, Any]):
    import bpy

    scene = bpy.context.scene
    lights = [o for o in scene.objects if o.type == "LIGHT" and not o.hide_render]
    world_strength = None
    world = scene.world
    if world and world.use_nodes:
        bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
        if bg:
            world_strength = bg.inputs["Strength"].default_value
    issues, tips = [], []
    if not lights and not world_strength:
        issues.append("Scene has no lights and no world lighting: renders will be black")
    if len(lights) == 1:
        tips.append("Single light source: add fill/rim lights for shape (create_studio_lighting)")
    if lights:
        energies = sorted(o.data.energy for o in lights if o.data.type != "SUN")
        if len(energies) >= 2 and energies[-1] / max(energies[0], 1e-6) > 50:
            tips.append("Very high key:fill ratio; contrast may be harsh")
        if all(o.data.type == "POINT" for o in lights):
            tips.append("Only point lights: area lights give softer, more realistic shadows")
    if scene.view_settings.view_transform == "Standard":
        tips.append("View transform 'Standard' clips highlights; use AgX or Filmic")
    if scene.camera is None:
        issues.append("No active camera")
    return {
        "lights": [
            {
                "name": o.name,
                "type": o.data.type,
                "energy": o.data.energy,
                "color": [round(c, 3) for c in o.data.color],
            }
            for o in lights
        ],
        "world_strength": world_strength,
        "view_transform": scene.view_settings.view_transform,
        "exposure": scene.view_settings.exposure,
        "issues": issues,
        "suggestions": tips,
    }


# ---------------------------------------------------------------- camera helpers


@command("camera_track_object")
def camera_track_object(params: dict[str, Any]):
    cam = get_object(params["camera"])
    target = get_object(params["target"])
    con = next((c for c in cam.constraints if c.type in {"TRACK_TO", "DAMPED_TRACK"}), None)
    con = con or cam.constraints.new("TRACK_TO")
    con.target = target
    if con.type == "TRACK_TO":
        con.track_axis, con.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    if cam.type == "CAMERA" and params.get("focus", True):
        cam.data.dof.focus_object = target
    return {"camera": cam.name, "target": target.name}


@command("create_camera_rig")
def create_camera_rig(params: dict[str, Any]):
    """Rigs: orbit (pivot), dolly (path move), crane (raise + tilt), handheld (noise shake)."""
    import bpy
    import mathutils

    from .animation_advanced import iter_fcurves

    kind = (params.get("rig") or "orbit").lower()
    target = get_object(params["target"]) if params.get("target") else None
    center = target.matrix_world.translation.copy() if target else mathutils.Vector()
    start = int(params.get("frame_start") or 1)
    frames = int(params.get("frames") or 120)
    dist = float(params.get("distance") or 8.0)
    coll = params.get("collection") or "Camera_Rig"
    cam_data = bpy.data.cameras.new(f"{kind}_Cam")
    cam_data.lens = float(params.get("focal_length") or 50)
    cam = bpy.data.objects.new(f"{kind}_Cam", cam_data)
    link_object(cam, coll)
    root = bpy.data.objects.new(f"{kind}_Rig", None)
    link_object(root, coll)
    root.location = center
    cam.parent = root
    track = cam.constraints.new("TRACK_TO")
    track.target = target or root
    track.track_axis, track.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    end = start + frames
    if kind == "orbit":
        cam.location = (0, -dist, dist * 0.3)
        root.rotation_euler.z = 0
        root.keyframe_insert("rotation_euler", index=2, frame=start)
        root.rotation_euler.z = math.radians(float(params.get("angle") or 360))
        root.keyframe_insert("rotation_euler", index=2, frame=end)
    elif kind == "dolly":
        cam.location = (-dist * 0.5, -dist, dist * 0.2)
        cam.keyframe_insert("location", frame=start)
        cam.location = (dist * 0.5, -dist * 0.7, dist * 0.2)
        cam.keyframe_insert("location", frame=end)
    elif kind == "crane":
        cam.location = (0, -dist, 0.5)
        cam.keyframe_insert("location", frame=start)
        cam.location = (0, -dist * 0.8, dist)
        cam.keyframe_insert("location", frame=end)
    elif kind == "handheld":
        cam.location = (0, -dist, dist * 0.2)
        cam.keyframe_insert("location", frame=start)
        cam.keyframe_insert("rotation_euler", frame=start)
        for fc in iter_fcurves(cam):
            mod = fc.modifiers.new("NOISE")
            mod.scale, mod.strength = 20.0, 0.05 if fc.data_path == "location" else 0.02
    else:
        raise ValueError("rig must be orbit, dolly, crane or handheld")
    for owner in (cam, root):
        for fc in iter_fcurves(owner):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR" if kind == "orbit" else "BEZIER"
    if params.get("set_active", True):
        bpy.context.scene.camera = cam
    return {"camera": cam.name, "rig": root.name, "type": kind, "frame_range": [start, end]}


@command("set_camera_composition")
def set_camera_composition(params: dict[str, Any]):
    cam = get_object(params["camera"])
    data = cam.data
    guides = [g.lower() for g in params.get("guides") or ["thirds"]]
    data.show_composition_thirds = "thirds" in guides
    data.show_composition_center = "center" in guides
    data.show_composition_golden = "golden" in guides
    data.show_composition_harmony_tri_a = "harmony" in guides
    if params.get("sensor_fit"):
        data.sensor_fit = params["sensor_fit"].upper()
    if params.get("aspect"):
        import bpy

        w, h = params["aspect"]
        r = bpy.context.scene.render
        r.resolution_y = int(r.resolution_x * float(h) / float(w))
    if params.get("shift") is not None:
        data.shift_x, data.shift_y = params["shift"]
    return {"camera": cam.name, "guides": guides}


@command("create_camera_views")
def create_camera_views(params: dict[str, Any]):
    """Create several named cameras around a target: front, back, left, right, top, three_quarter,
    low_angle, closeup."""
    import bpy
    import mathutils

    target = get_object(params["target"])
    center = target.matrix_world.translation.copy()
    size = max(max(target.dimensions), 0.5)
    d = size * float(params.get("distance_factor") or 2.5)
    presets = {
        "front": (0, -1, 0.2),
        "back": (0, 1, 0.2),
        "left": (-1, 0, 0.2),
        "right": (1, 0, 0.2),
        "top": (0, -0.01, 1),
        "three_quarter": (0.8, -0.8, 0.5),
        "low_angle": (0.3, -1, -0.15),
        "closeup": (0.4, -0.6, 0.25),
    }
    views = params.get("views") or ["front", "three_quarter", "top"]
    coll = params.get("collection") or "Camera_Views"
    created = []
    for v in views:
        if v not in presets:
            raise ValueError(f"Unknown view {v!r}; valid: {list(presets)}")
        data = bpy.data.cameras.new(f"Cam_{v}")
        data.lens = 85 if v == "closeup" else 50
        cam = bpy.data.objects.new(f"Cam_{v}", data)
        link_object(cam, coll)
        factor = 0.5 if v == "closeup" else 1.0
        cam.location = center + mathutils.Vector(presets[v]).normalized() * d * factor
        cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
        data.dof.focus_object = target
        created.append(cam.name)
    return {"cameras": created, "target": target.name}
