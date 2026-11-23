"""Sculpting and UV-mapping MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.tools.registry import forward_params as P

Brush = Literal[
    "draw",
    "clay",
    "clay_strips",
    "inflate",
    "smooth",
    "grab",
    "crease",
    "flatten",
    "scrape",
    "pinch",
    "snake_hook",
    "layer",
    "blob",
    "mask",
]
Deform = Literal[
    "draw",
    "clay",
    "inflate",
    "deflate",
    "smooth",
    "grab",
    "crease",
    "flatten",
    "scrape",
    "pinch",
    "snake_hook",
    "noise",
]


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="set_sculpt_mode")
    async def set_sculpt_mode(name: str, enable: bool = True) -> dict[str, Any]:
        """Enter (or leave) Sculpt Mode on a mesh object."""
        return await call_blender(ctx, "set_sculpt_mode", P(locals()), group="sculpting")

    @mcp.tool(name="set_sculpt_brush")
    async def set_sculpt_brush(
        brush: Brush = "draw",
        strength: float | None = None,
        radius_px: int | None = None,
        direction: Literal["ADD", "SUBTRACT"] | None = None,
    ) -> dict[str, Any]:
        """Select a sculpt brush (4.3+ essentials assets or legacy brushes) and set
        strength/radius."""
        return await call_blender(ctx, "set_sculpt_brush", P(locals()), group="sculpting")

    @mcp.tool(name="sculpt_deform")
    async def sculpt_deform(
        name: str,
        operation: Deform = "draw",
        center: list[float] | None = None,
        radius: float = 0.5,
        strength: float = 0.5,
        direction: list[float] | None = None,
        falloff: Literal["smooth", "linear", "sharp", "constant"] = "smooth",
        iterations: int = 1,
    ) -> dict[str, Any]:
        """Brush-style sculpt deformation at a world-space point (works headless, deterministic).

        Covers draw/clay/inflate/deflate/smooth/grab/snake_hook/crease/flatten/scrape/pinch/noise.
        ``direction`` drives grab/snake_hook. Respects the sculpt mask. Subdivide or remesh first
        for detail: deformation needs enough vertices inside ``radius``.
        """
        return await call_blender(ctx, "sculpt_deform", P(locals()), group="sculpting")

    @mcp.tool(name="sculpt_stroke")
    async def sculpt_stroke(
        name: str,
        points: list[list[float]],
        brush: Brush | None = None,
        radius_px: float = 50,
        pressure: float = 1.0,
        invert: bool = False,
    ) -> dict[str, Any]:
        """Real sculpt brush stroke through world-space points. Needs a visible 3D viewport."""
        return await call_blender(ctx, "sculpt_stroke", P(locals()), group="sculpting")

    @mcp.tool(name="sculpt_mask")
    async def sculpt_mask(
        name: str,
        action: Literal[
            "clear", "fill", "invert", "sphere", "vertex_group", "above_z", "below_z"
        ] = "clear",
        value: float = 1.0,
        center: list[float] | None = None,
        radius: float | None = None,
        vertex_group: str | None = None,
    ) -> dict[str, Any]:
        """Edit the sculpt mask (masked vertices are protected from sculpt_deform)."""
        return await call_blender(ctx, "sculpt_mask", P(locals()), group="sculpting")

    @mcp.tool(name="sculpt_face_sets")
    async def sculpt_face_sets(
        name: str,
        mode: Literal[
            "LOOSE_PARTS", "MATERIALS", "NORMALS", "UV_SEAMS", "CREASES", "SHARP_EDGES"
        ] = "LOOSE_PARTS",
    ) -> dict[str, Any]:
        """Initialise sculpt face sets from mesh features."""
        return await call_blender(ctx, "sculpt_face_sets", P(locals()), group="sculpting")

    @mcp.tool(name="set_dynamic_topology")
    async def set_dynamic_topology(
        name: str,
        enable: bool = True,
        detail_size: float | None = None,
        detail_type: Literal["RELATIVE", "CONSTANT", "BRUSH", "MANUAL"] | None = None,
    ) -> dict[str, Any]:
        """Toggle Dyntopo in Sculpt Mode and set its detail."""
        return await call_blender(ctx, "set_dynamic_topology", P(locals()), group="sculpting")

    @mcp.tool(name="voxel_remesh")
    async def voxel_remesh(
        name: str,
        voxel_size: float = 0.05,
        adaptivity: float = 0.0,
        preserve_volume: bool = True,
    ) -> dict[str, Any]:
        """Voxel remesh for uniform sculpting topology (destructive to existing topology)."""
        return await call_blender(ctx, "voxel_remesh", P(locals()), group="sculpting")

    @mcp.tool(name="add_multires")
    async def add_multires(
        name: str, levels: int = 2, viewport_levels: int | None = None
    ) -> dict[str, Any]:
        """Add a Multiresolution modifier and subdivide it ``levels`` times (max 6)."""
        return await call_blender(ctx, "add_multires", P(locals()), group="sculpting")

    # ------------------------------------------------------------------ UV

    @mcp.tool(name="uv_unwrap")
    async def uv_unwrap(
        name: str,
        method: Literal[
            "smart", "unwrap", "cube", "cylinder", "sphere", "lightmap", "project_view"
        ] = "smart",
        angle_limit: float = 66.0,
        island_margin: float = 0.02,
        cube_size: float | None = None,
        uv_map: str | None = None,
    ) -> dict[str, Any]:
        """UV unwrap a mesh. ``unwrap`` respects marked seams; ``uv_map`` targets/creates a
        layer."""
        return await call_blender(ctx, "uv_unwrap", P(locals()), group="uv")

    @mcp.tool(name="mark_uv_seams")
    async def mark_uv_seams(
        name: str,
        mode: Literal["sharp", "boundary", "indices", "clear"] = "sharp",
        angle: float = 30.0,
        edge_indices: list[int] | None = None,
    ) -> dict[str, Any]:
        """Mark UV seams on sharp edges (by angle), boundaries, explicit edges, or clear them."""
        return await call_blender(ctx, "mark_uv_seams", P(locals()), group="uv")

    @mcp.tool(name="pack_uv_islands")
    async def pack_uv_islands(
        name: str, margin: float = 0.02, rotate: bool = True
    ) -> dict[str, Any]:
        """Average island scale and pack UV islands into 0..1."""
        return await call_blender(ctx, "pack_uv_islands", P(locals()), group="uv")

    @mcp.tool(name="get_uv_info")
    async def get_uv_info(name: str) -> dict[str, Any]:
        """UV maps, seams, out-of-bounds loops and zero-area UV faces."""
        return await call_blender(ctx, "get_uv_info", P(locals()), group="uv")
