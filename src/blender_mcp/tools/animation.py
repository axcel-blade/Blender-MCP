"""Animation MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="create_keyframe")
    async def create_keyframe(
        name: str,
        data_path: str,
        frame: int | None = None,
        index: int = -1,
    ) -> dict[str, Any]:
        """Insert a keyframe on an object."""
        return await call_blender(ctx, "create_keyframe", {"name": name, "data_path": data_path, "frame": frame, "index": index}, group="animation")

    @mcp.tool(name="set_keyframe")
    async def set_keyframe(
        name: str,
        data_path: str,
        value: Any,
        frame: int | None = None,
    ) -> dict[str, Any]:
        """Set a property value and keyframe it."""
        return await call_blender(ctx, "set_keyframe", {"name": name, "data_path": data_path, "value": value, "frame": frame}, group="animation")

    @mcp.tool(name="remove_keyframe")
    async def remove_keyframe(
        name: str,
        data_path: str,
        frame: int | None = None,
    ) -> dict[str, Any]:
        """Remove a keyframe."""
        return await call_blender(ctx, "remove_keyframe", {"name": name, "data_path": data_path, "frame": frame}, group="animation")

    @mcp.tool(name="animate_location")
    async def animate_location(
        name: str,
        location: list[float],
        frame: int,
    ) -> dict[str, Any]:
        """Keyframe object location."""
        return await call_blender(ctx, "animate_location", {"name": name, "location": location, "frame": frame}, group="animation")

    @mcp.tool(name="animate_rotation")
    async def animate_rotation(
        name: str,
        rotation: list[float],
        frame: int,
    ) -> dict[str, Any]:
        """Keyframe object rotation."""
        return await call_blender(ctx, "animate_rotation", {"name": name, "rotation": rotation, "frame": frame}, group="animation")

    @mcp.tool(name="animate_scale")
    async def animate_scale(
        name: str,
        scale: list[float],
        frame: int,
    ) -> dict[str, Any]:
        """Keyframe object scale."""
        return await call_blender(ctx, "animate_scale", {"name": name, "scale": scale, "frame": frame}, group="animation")

    @mcp.tool(name="set_animation_range")
    async def set_animation_range(
        frame_start: int,
        frame_end: int,
    ) -> dict[str, Any]:
        """Set scene animation range."""
        return await call_blender(ctx, "set_animation_range", {"frame_start": frame_start, "frame_end": frame_end}, group="animation")

    @mcp.tool(name="set_current_frame")
    async def set_current_frame(
        frame: int,
    ) -> dict[str, Any]:
        """Set the current frame."""
        return await call_blender(ctx, "set_current_frame", {"frame": frame}, group="animation")

    @mcp.tool(name="inspect_animation")
    async def inspect_animation(
        name: str | None = None,
    ) -> dict[str, Any]:
        """Inspect animation data."""
        return await call_blender(ctx, "inspect_animation", {"name": name}, group="animation")

    @mcp.tool(name="create_animation_preview")
    async def create_animation_preview(
        frame_start: int | None = None,
        frame_end: int | None = None,
        step: int = 5,
    ) -> dict[str, Any]:
        """Capture frames for an animation preview strip."""
        return await call_blender(ctx, "create_animation_preview", {"frame_start": frame_start, "frame_end": frame_end, "step": step}, group="animation")

