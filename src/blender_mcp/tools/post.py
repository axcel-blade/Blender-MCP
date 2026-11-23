"""Compositing, video editing (VSE) and Grease Pencil 2D MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender, call_blender_paths
from blender_mcp.tools.registry import forward_params as P

Effect = Literal[
    "glare",
    "bloom",
    "blur",
    "color_grade",
    "vignette",
    "denoise",
    "lens_distortion",
    "sharpen",
    "brightness_contrast",
    "exposure",
]


def register(mcp: FastMCP, ctx: AppContext) -> None:

    # ------------------------------------------------------------------ compositor

    @mcp.tool(name="enable_compositor")
    async def enable_compositor() -> dict[str, Any]:
        """Enable compositing with a Render Layers -> output chain (Blender 4.x and 5.x)."""
        return await call_blender(ctx, "enable_compositor", {}, group="compositing")

    @mcp.tool(name="add_compositor_node")
    async def add_compositor_node(
        node_type: str,
        name: str | None = None,
        location: list[float] | None = None,
        inputs: dict[str, Any] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add any compositor node by bl_idname (e.g. CompositorNodeGlare, CompositorNodeKeying)."""
        return await call_blender(ctx, "add_compositor_node", P(locals()), group="compositing")

    @mcp.tool(name="connect_compositor_nodes")
    async def connect_compositor_nodes(
        from_node: str,
        to_node: str,
        from_socket: str | int = 0,
        to_socket: str | int = 0,
    ) -> dict[str, Any]:
        """Link two compositor nodes by socket name or index."""
        return await call_blender(ctx, "connect_compositor_nodes", P(locals()), group="compositing")

    @mcp.tool(name="set_compositor_node")
    async def set_compositor_node(
        node: str,
        inputs: dict[str, Any] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Edit a compositor node's input values or properties."""
        return await call_blender(ctx, "set_compositor_node", P(locals()), group="compositing")

    @mcp.tool(name="remove_compositor_node")
    async def remove_compositor_node(node: str) -> dict[str, Any]:
        """Remove a compositor node."""
        return await call_blender(ctx, "remove_compositor_node", P(locals()), group="compositing")

    @mcp.tool(name="apply_compositor_effect")
    async def apply_compositor_effect(
        effect: Effect, settings: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Stack a finished post effect before the output: glare/bloom (threshold, strength), blur
        (size),
        color_grade (lift/gamma/gain RGB, saturation), vignette, denoise, lens_distortion
        (distortion, dispersion), sharpen (amount), brightness_contrast, exposure."""
        return await call_blender(ctx, "apply_compositor_effect", P(locals()), group="compositing")

    @mcp.tool(name="composite_over_image")
    async def composite_over_image(path: str) -> dict[str, Any]:
        """Alpha-over the render onto a background image (enables transparent film)."""
        return await call_blender_paths(
            ctx, "composite_over_image", P(locals()), group="compositing"
        )

    @mcp.tool(name="get_compositor_info")
    async def get_compositor_info() -> dict[str, Any]:
        """Compositor nodes and links."""
        return await call_blender(ctx, "get_compositor_info", {}, group="compositing")

    # ------------------------------------------------------------------ video editing

    @mcp.tool(name="vse_add_strip")
    async def vse_add_strip(
        kind: Literal["movie", "sound", "image", "color"] = "movie",
        path: str | None = None,
        name: str | None = None,
        channel: int = 1,
        frame_start: int = 1,
        length: int | None = None,
        with_audio: bool = True,
        volume: float | None = None,
        color: list[float] | None = None,
        fit_scene_range: bool = True,
    ) -> dict[str, Any]:
        """Import video/audio/image into the Video Sequencer (or a solid colour strip)."""
        return await call_blender_paths(ctx, "vse_add_strip", P(locals()), group="video_editing")

    @mcp.tool(name="vse_add_text")
    async def vse_add_text(
        text: str,
        frame_start: int = 1,
        length: int = 72,
        channel: int = 5,
        size: float = 60,
        color: list[float] | None = None,
        location: list[float] | None = None,
        shadow: bool | None = None,
        box: bool | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Titles, captions and lower thirds (location in 0..1 screen space)."""
        return await call_blender(ctx, "vse_add_text", P(locals()), group="video_editing")

    @mcp.tool(name="vse_add_transition")
    async def vse_add_transition(
        strip_a: str,
        strip_b: str,
        transition: Literal["CROSS", "GAMMA_CROSS", "WIPE"] = "CROSS",
        length: int = 12,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Crossfade/wipe between two strips (moves strip_b to overlap when needed)."""
        return await call_blender(ctx, "vse_add_transition", P(locals()), group="video_editing")

    @mcp.tool(name="vse_add_effect")
    async def vse_add_effect(
        effect: str = "ADJUSTMENT",
        strip: str | None = None,
        frame_start: int | None = None,
        length: int | None = None,
        channel: int | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Strip effects (SPEED, GLOW, GAUSSIAN_BLUR, COLORMIX, ADJUSTMENT; TRANSFORM only on
        older Blender) or strip modifiers (COLOR_BALANCE, CURVES, HUE_CORRECT, BRIGHT_CONTRAST,
        WHITE_BALANCE, TONEMAP)."""
        return await call_blender(ctx, "vse_add_effect", P(locals()), group="video_editing")

    @mcp.tool(name="vse_edit_strip")
    async def vse_edit_strip(
        name: str,
        frame_start: float | None = None,
        channel: int | None = None,
        trim_start: float | None = None,
        trim_end: float | None = None,
        mute: bool | None = None,
        opacity: float | None = None,
        blend_type: str | None = None,
        volume: float | None = None,
        fade_in: int | None = None,
        fade_out: int | None = None,
    ) -> dict[str, Any]:
        """Move, trim, mute, fade, blend or change volume of a strip."""
        return await call_blender(ctx, "vse_edit_strip", P(locals()), group="video_editing")

    @mcp.tool(name="vse_cut_strip")
    async def vse_cut_strip(name: str, frame: int) -> dict[str, Any]:
        """Split a movie or sound strip at a frame."""
        return await call_blender(ctx, "vse_cut_strip", P(locals()), group="video_editing")

    @mcp.tool(name="vse_remove_strip")
    async def vse_remove_strip(name: str, confirmed: bool = False) -> dict[str, Any]:
        """Remove a strip (requires confirmed=true)."""
        return await call_blender(ctx, "vse_remove_strip", P(locals()), group="video_editing")

    @mcp.tool(name="vse_list_strips")
    async def vse_list_strips() -> Any:
        """Timeline contents sorted by channel and start frame."""
        return await call_blender(ctx, "vse_list_strips", {}, group="video_editing")

    @mcp.tool(name="vse_sync_audio")
    async def vse_sync_audio(
        match_fps_of: str | None = None,
        align_strip: str | None = None,
        to_frame: float | None = None,
    ) -> dict[str, Any]:
        """Audio-synced playback, scene fps matched to footage, strips aligned, range fitted."""
        return await call_blender(ctx, "vse_sync_audio", P(locals()), group="video_editing")

    @mcp.tool(name="vse_render_video")
    async def vse_render_video(
        path: str,
        container_format: Literal["MP4", "MOV", "MKV", "WEBM"] = "MP4",
        codec: str | None = None,
        audio_codec: str = "AAC",
        quality: str | None = None,
        resolution: list[int] | None = None,
    ) -> dict[str, Any]:
        """Render the edit to a video file with audio."""
        return await call_blender_paths(
            ctx, "vse_render_video", P(locals()), group="video_editing", must_exist=False
        )

    # ------------------------------------------------------------------ grease pencil

    @mcp.tool(name="create_grease_pencil")
    async def create_grease_pencil(
        name: str = "GPencil",
        layer: str = "Lines",
        location: list[float] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a Grease Pencil object for 2D drawing/animation (GPv2 and GPv3 supported)."""
        return await call_blender(ctx, "create_grease_pencil", P(locals()), group="grease_pencil")

    @mcp.tool(name="draw_grease_pencil_stroke")
    async def draw_grease_pencil_stroke(
        name: str,
        points: list[list[float]],
        layer: str = "Lines",
        frame: int | None = None,
        radius: float = 0.02,
        color: list[float] | None = None,
        fill_color: list[float] | None = None,
        cyclic: bool = False,
    ) -> dict[str, Any]:
        """Draw a stroke from local points (XZ is the front drawing plane)."""
        return await call_blender(
            ctx, "draw_grease_pencil_stroke", P(locals()), group="grease_pencil"
        )

    @mcp.tool(name="draw_grease_pencil_shape")
    async def draw_grease_pencil_shape(
        name: str,
        shape: Literal[
            "line", "circle", "polygon", "rectangle", "star", "spiral", "wave"
        ] = "circle",
        size: float = 1.0,
        sides: int = 5,
        center: list[float] | None = None,
        layer: str = "Lines",
        frame: int | None = None,
        radius: float = 0.02,
        color: list[float] | None = None,
        fill_color: list[float] | None = None,
    ) -> dict[str, Any]:
        """Draw a 2D shape stroke (optionally filled)."""
        return await call_blender(
            ctx, "draw_grease_pencil_shape", P(locals()), group="grease_pencil"
        )

    @mcp.tool(name="animate_grease_pencil")
    async def animate_grease_pencil(
        name: str, frames: list[dict[str, Any]], layer: str = "Animation"
    ) -> dict[str, Any]:
        """Frame-by-frame 2D animation: [{frame, strokes: [{points, color?, radius?, cyclic?}]}]."""
        return await call_blender(ctx, "animate_grease_pencil", P(locals()), group="grease_pencil")

    @mcp.tool(name="add_grease_pencil_modifier")
    async def add_grease_pencil_modifier(
        name: str,
        modifier_type: str,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Grease Pencil modifiers: NOISE, SMOOTH, THICKNESS, BUILD (draw-on), TINT, OFFSET, ..."""
        return await call_blender(
            ctx, "add_grease_pencil_modifier", P(locals()), group="grease_pencil"
        )

    @mcp.tool(name="get_grease_pencil_info")
    async def get_grease_pencil_info(name: str) -> dict[str, Any]:
        """Layers, frames and stroke counts."""
        return await call_blender(ctx, "get_grease_pencil_info", P(locals()), group="grease_pencil")
