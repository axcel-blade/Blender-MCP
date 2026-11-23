"""Render engine configuration, lighting design and cinematography MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender, call_blender_paths
from blender_mcp.tools.registry import forward_params as P


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="configure_cycles")
    async def configure_cycles(
        samples: int | None = None,
        preview_samples: int | None = None,
        device: Literal["CPU", "GPU"] | None = None,
        compute_type: Literal["OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"] | None = None,
        denoise: bool | None = None,
        denoiser: Literal["OPENIMAGEDENOISE", "OPTIX"] | None = None,
        adaptive_threshold: float | None = None,
        max_bounces: int | None = None,
        time_limit: float | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Switch to Cycles and set samples, denoising, bounces and CPU/GPU (auto-picks a GPU
        backend)."""
        return await call_blender(ctx, "configure_cycles", P(locals()), group="rendering")

    @mcp.tool(name="configure_eevee")
    async def configure_eevee(
        samples: int | None = None,
        raytracing: bool | None = None,
        shadows: bool | None = None,
        volumetrics_resolution: Literal["2", "4", "8", "16"] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Switch to EEVEE (Next on 4.2+) and configure it."""
        return await call_blender(ctx, "configure_eevee", P(locals()), group="rendering")

    @mcp.tool(name="configure_workbench")
    async def configure_workbench(
        lighting: Literal["STUDIO", "MATCAP", "FLAT"] | None = None,
        color_type: Literal["MATERIAL", "OBJECT", "SINGLE", "RANDOM", "TEXTURE", "VERTEX"]
        | None = None,
        show_cavity: bool | None = None,
        show_outline: bool | None = None,
    ) -> dict[str, Any]:
        """Workbench engine for fast clay/technical renders."""
        return await call_blender(ctx, "configure_workbench", P(locals()), group="rendering")

    @mcp.tool(name="configure_render_passes")
    async def configure_render_passes(passes: list[str], enable: bool = True) -> dict[str, Any]:
        """Enable passes (z, mist, normal, vector, ao, emission, shadow, diffuse_color,
        cryptomatte_object, cryptomatte_material, ...) for compositing."""
        return await call_blender(ctx, "configure_render_passes", P(locals()), group="rendering")

    @mcp.tool(name="set_color_management")
    async def set_color_management(
        view_transform: str | None = None,
        look: str | None = None,
        exposure: float | None = None,
        gamma: float | None = None,
        display_device: str | None = None,
    ) -> dict[str, Any]:
        """View transform (AgX, Filmic, Standard, Khronos PBR Neutral...), look (contrast),
        exposure."""
        return await call_blender(ctx, "set_color_management", P(locals()), group="rendering")

    @mcp.tool(name="set_output_format")
    async def set_output_format(
        file_format: str = "PNG",
        color_depth: str | None = None,
        color_mode: str | None = None,
        compression: int | None = None,
        container: str | None = None,
        codec: str | None = None,
        quality: str | None = None,
        audio_codec: str | None = None,
        film_transparent: bool | None = None,
    ) -> dict[str, Any]:
        """Image (PNG, JPEG, OPEN_EXR, OPEN_EXR_MULTILAYER, TIFF, WEBP) or video (MP4, MOV, MKV,
        WEBM)."""
        return await call_blender(ctx, "set_output_format", P(locals()), group="rendering")

    @mcp.tool(name="optimize_render_settings")
    async def optimize_render_settings(
        profile: Literal["draft", "preview", "balanced", "final", "cinematic"] = "balanced",
    ) -> dict[str, Any]:
        """Speed/quality profile for the current engine; also flags very heavy objects."""
        return await call_blender(ctx, "optimize_render_settings", P(locals()), group="rendering")

    @mcp.tool(name="batch_render")
    async def batch_render(
        output_dir: str,
        cameras: list[str] | None = None,
        frames: list[int] | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Render a still for every camera (default: all) and frame into ``output_dir``."""
        return await call_blender_paths(
            ctx,
            "batch_render",
            P(locals()),
            group="rendering",
            path_keys=("output_dir",),
            must_exist=False,
        )

    # ------------------------------------------------------------------ lighting

    @mcp.tool(name="set_light_properties")
    async def set_light_properties(
        name: str,
        energy: float | None = None,
        color: list[float] | None = None,
        temperature: float | None = None,
        size: float | None = None,
        cast_shadows: bool | None = None,
        spot_angle: float | None = None,
        spot_blend: float | None = None,
        area_shape: Literal["SQUARE", "RECTANGLE", "DISK", "ELLIPSE"] | None = None,
    ) -> dict[str, Any]:
        """Intensity, colour or colour temperature (Kelvin), size/softness, shadows, spot cone."""
        return await call_blender(ctx, "set_light_properties", P(locals()), group="lighting")

    @mcp.tool(name="create_studio_lighting")
    async def create_studio_lighting(
        style: Literal[
            "three_point",
            "softbox",
            "rembrandt",
            "rim",
            "high_key",
            "low_key",
            "product",
            "noir",
            "golden_hour",
        ] = "three_point",
        target: str | None = None,
        distance_scale: float = 1.0,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Professional light rigs sized and aimed to the target, with realistic colour
        temperatures."""
        return await call_blender(ctx, "create_studio_lighting", P(locals()), group="lighting")

    @mcp.tool(name="analyze_lighting")
    async def analyze_lighting() -> dict[str, Any]:
        """Audit illumination: lights, world strength, contrast, view transform; suggests fixes."""
        return await call_blender(ctx, "analyze_lighting", {}, group="lighting")

    # ------------------------------------------------------------------ cameras

    @mcp.tool(name="camera_track_object")
    async def camera_track_object(camera: str, target: str, focus: bool = True) -> dict[str, Any]:
        """Keep a camera aimed at (and focused on) a moving object."""
        return await call_blender(ctx, "camera_track_object", P(locals()), group="cameras")

    @mcp.tool(name="create_camera_rig")
    async def create_camera_rig(
        rig: Literal["orbit", "dolly", "crane", "handheld"] = "orbit",
        target: str | None = None,
        distance: float = 8.0,
        focal_length: float = 50,
        frame_start: int = 1,
        frames: int = 120,
        angle: float = 360,
        set_active: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Animated cinematic camera rigs: orbit, dolly slide, crane up, handheld shake."""
        return await call_blender(ctx, "create_camera_rig", P(locals()), group="cameras")

    @mcp.tool(name="set_camera_composition")
    async def set_camera_composition(
        camera: str,
        guides: list[Literal["thirds", "center", "golden", "harmony"]] | None = None,
        aspect: list[float] | None = None,
        shift: list[float] | None = None,
        sensor_fit: Literal["AUTO", "HORIZONTAL", "VERTICAL"] | None = None,
    ) -> dict[str, Any]:
        """Composition guides, aspect ratio (e.g. [2.39, 1] cinemascope) and lens shift."""
        return await call_blender(ctx, "set_camera_composition", P(locals()), group="cameras")

    @mcp.tool(name="create_camera_views")
    async def create_camera_views(
        target: str,
        views: list[
            Literal[
                "front", "back", "left", "right", "top", "three_quarter", "low_angle", "closeup"
            ]
        ]
        | None = None,
        distance_factor: float = 2.5,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create several framed viewpoint cameras around a subject."""
        return await call_blender(ctx, "create_camera_views", P(locals()), group="cameras")
