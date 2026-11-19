"""Scene inspection MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="get_scene_info")
    async def get_scene_info() -> dict[str, Any]:
        """Return detailed information about the current Blender scene."""
        return await call_blender(ctx, "get_scene_info", {}, group="scene")

    @mcp.tool(name="get_scene_summary")
    async def get_scene_summary() -> dict[str, Any]:
        """Return a compact summary of the current scene."""
        return await call_blender(ctx, "get_scene_summary", {}, group="scene")

    @mcp.tool(name="get_scene_hierarchy")
    async def get_scene_hierarchy() -> dict[str, Any]:
        """Return the scene collection hierarchy."""
        return await call_blender(ctx, "get_scene_hierarchy", {}, group="scene")

    @mcp.tool(name="get_objects")
    async def get_objects(
        name_filter: str | None = None,
        object_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List objects with optional filtering and pagination."""
        return await call_blender(
            ctx,
            "get_objects",
            {
                "name_filter": name_filter,
                "object_type": object_type,
                "limit": limit,
                "offset": offset,
            },
            group="scene",
        )

    @mcp.tool(name="get_object_info")
    async def get_object_info(
        name: str,
    ) -> dict[str, Any]:
        """Get detailed info for a single object by name."""
        return await call_blender(ctx, "get_object_info", {"name": name}, group="scene")

    @mcp.tool(name="get_selected_objects")
    async def get_selected_objects() -> dict[str, Any]:
        """List currently selected objects."""
        return await call_blender(ctx, "get_selected_objects", {}, group="scene")

    @mcp.tool(name="get_active_object")
    async def get_active_object() -> dict[str, Any]:
        """Return the active object, if any."""
        return await call_blender(ctx, "get_active_object", {}, group="scene")

    @mcp.tool(name="get_collections")
    async def get_collections() -> dict[str, Any]:
        """List collections in the scene."""
        return await call_blender(ctx, "get_collections", {}, group="scene")

    @mcp.tool(name="get_object_transform")
    async def get_object_transform(
        name: str,
        space: str = "world",
    ) -> dict[str, Any]:
        """Get location/rotation/scale for an object."""
        return await call_blender(
            ctx, "get_object_transform", {"name": name, "space": space}, group="scene"
        )

    @mcp.tool(name="get_mesh_statistics")
    async def get_mesh_statistics(
        name: str | None = None,
    ) -> dict[str, Any]:
        """Get mesh statistics for an object or the whole scene."""
        return await call_blender(ctx, "get_mesh_statistics", {"name": name}, group="scene")

    @mcp.tool(name="get_scene_settings")
    async def get_scene_settings() -> dict[str, Any]:
        """Get unit/frame/gravity and related scene settings."""
        return await call_blender(ctx, "get_scene_settings", {}, group="scene")

    @mcp.tool(name="get_camera_info")
    async def get_camera_info(
        name: str | None = None,
    ) -> dict[str, Any]:
        """Get camera information."""
        return await call_blender(ctx, "get_camera_info", {"name": name}, group="scene")

    @mcp.tool(name="get_materials")
    async def get_materials() -> dict[str, Any]:
        """List materials in the blend file."""
        return await call_blender(ctx, "get_materials", {}, group="scene")

    @mcp.tool(name="get_lights")
    async def get_lights() -> dict[str, Any]:
        """List lights in the scene."""
        return await call_blender(ctx, "get_lights", {}, group="scene")

    @mcp.tool(name="get_modifiers")
    async def get_modifiers(
        name: str,
    ) -> dict[str, Any]:
        """List modifiers on an object."""
        return await call_blender(ctx, "get_modifiers", {"name": name}, group="scene")

    @mcp.tool(name="get_animation_info")
    async def get_animation_info() -> dict[str, Any]:
        """Summarize animation data and timeline."""
        return await call_blender(ctx, "get_animation_info", {}, group="scene")

    @mcp.tool(name="get_current_frame")
    async def get_current_frame() -> dict[str, Any]:
        """Get the current frame number."""
        return await call_blender(ctx, "get_current_frame", {}, group="scene")

    @mcp.tool(name="diagnose_blender_connection")
    async def diagnose_blender_connection() -> dict[str, Any]:
        """Diagnose MCP-to-Blender connectivity and capabilities."""
        return await call_blender(ctx, "diagnose_blender_connection", {}, group="scene")
