"""Rendering MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="render_scene")
    async def render_scene(
        engine: str | None = None,
        samples: int | None = None,
        resolution_percentage: int = 50,
        write_still: bool = True,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Render the current frame."""
        return await call_blender(ctx, "render_scene", {"engine": engine, "samples": samples, "resolution_percentage": resolution_percentage, "write_still": write_still, "output_path": output_path}, group="rendering")

    @mcp.tool(name="render_preview")
    async def render_preview(
        resolution_percentage: int = 25,
        samples: int = 16,
    ) -> dict[str, Any]:
        """Render a fast preview image."""
        return await call_blender(ctx, "render_preview", {"resolution_percentage": resolution_percentage, "samples": samples, "preview": True}, group="rendering")

    @mcp.tool(name="render_final")
    async def render_final(
        output_path: str | None = None,
        samples: int | None = None,
    ) -> dict[str, Any]:
        """Render a higher-quality still."""
        return await call_blender(ctx, "render_final", {"output_path": output_path, "samples": samples, "final": True}, group="rendering")

    @mcp.tool(name="render_animation")
    async def render_animation(
        frame_start: int | None = None,
        frame_end: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Render an animation range."""
        return await call_blender(ctx, "render_animation", {"frame_start": frame_start, "frame_end": frame_end, "output_path": output_path}, group="rendering")

    @mcp.tool(name="get_render_settings")
    async def get_render_settings(
    
    ) -> dict[str, Any]:
        """Get render settings."""
        return await call_blender(ctx, "get_render_settings", {}, group="rendering")

    @mcp.tool(name="set_render_settings")
    async def set_render_settings(
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        """Update render settings with configured limits enforced."""
        return await call_blender(ctx, "set_render_settings", {"settings": settings}, group="rendering")

    @mcp.tool(name="set_output_path")
    async def set_output_path(
        path: str,
    ) -> dict[str, Any]:
        """Set render output path."""
        return await call_blender(ctx, "set_output_path", {"path": path}, group="rendering")

    @mcp.tool(name="get_render_result")
    async def get_render_result(
    
    ) -> dict[str, Any]:
        """Return the last render result path/metadata."""
        return await call_blender(ctx, "get_render_result", {}, group="rendering")

