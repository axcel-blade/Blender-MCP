"""Lighting MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="create_light")
    async def create_light(
        light_type: str = "POINT",
        name: str | None = None,
        location: list[float] | None = None,
        energy: float = 1000.0,
        color: list[float] | None = None,
    ) -> dict[str, Any]:
        """Create a light."""
        return await call_blender(ctx, "create_light", {"light_type": light_type, "name": name, "location": location, "energy": energy, "color": color}, group="lighting")

    @mcp.tool(name="modify_light")
    async def modify_light(
        name: str,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        """Modify light settings."""
        return await call_blender(ctx, "modify_light", {"name": name, "settings": settings}, group="lighting")

    @mcp.tool(name="delete_light")
    async def delete_light(
        name: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Delete a light object."""
        return await call_blender(ctx, "delete_light", {"name": name, "confirmed": confirmed}, group="lighting")

    @mcp.tool(name="get_light_info")
    async def get_light_info(
        name: str | None = None,
    ) -> dict[str, Any]:
        """Get light information."""
        return await call_blender(ctx, "get_light_info", {"name": name}, group="lighting")

    @mcp.tool(name="create_lighting_setup")
    async def create_lighting_setup(
        preset: str = "three_point",
        target: str | None = None,
    ) -> dict[str, Any]:
        """Create a lighting preset (three_point, studio, product, outdoor, interior, cinematic)."""
        return await call_blender(ctx, "create_lighting_setup", {"preset": preset, "target": target}, group="lighting")

