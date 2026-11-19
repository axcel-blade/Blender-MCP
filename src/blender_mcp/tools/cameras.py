"""Camera MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="create_camera")
    async def create_camera(
        name: str | None = None,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        lens: float = 50.0,
        set_active: bool = True,
    ) -> dict[str, Any]:
        """Create a camera."""
        return await call_blender(ctx, "create_camera", {"name": name, "location": location, "rotation": rotation, "lens": lens, "set_active": set_active}, group="cameras")

    @mcp.tool(name="modify_camera")
    async def modify_camera(
        name: str,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        """Modify camera settings."""
        return await call_blender(ctx, "modify_camera", {"name": name, "settings": settings}, group="cameras")

    @mcp.tool(name="set_active_camera")
    async def set_active_camera(
        name: str,
    ) -> dict[str, Any]:
        """Set the active scene camera."""
        return await call_blender(ctx, "set_active_camera", {"name": name}, group="cameras")

    @mcp.tool(name="focus_camera_on_object")
    async def focus_camera_on_object(
        camera: str,
        object_name: str,
    ) -> dict[str, Any]:
        """Point/focus a camera at an object."""
        return await call_blender(ctx, "focus_camera_on_object", {"camera": camera, "object_name": object_name}, group="cameras")

    @mcp.tool(name="frame_objects")
    async def frame_objects(
        camera: str | None = None,
        object_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Frame objects in a camera view."""
        return await call_blender(ctx, "frame_objects", {"camera": camera, "object_names": object_names}, group="cameras")

    @mcp.tool(name="configure_camera_lens")
    async def configure_camera_lens(
        name: str,
        lens: float | None = None,
        type: str | None = None,
        ortho_scale: float | None = None,
    ) -> dict[str, Any]:
        """Configure camera lens settings."""
        return await call_blender(ctx, "configure_camera_lens", {"name": name, "lens": lens, "type": type, "ortho_scale": ortho_scale}, group="cameras")

    @mcp.tool(name="configure_camera_depth_of_field")
    async def configure_camera_depth_of_field(
        name: str,
        enabled: bool = True,
        focus_object: str | None = None,
        focus_distance: float | None = None,
        fstop: float = 2.8,
    ) -> dict[str, Any]:
        """Configure camera depth of field."""
        return await call_blender(ctx, "configure_camera_depth_of_field", {"name": name, "enabled": enabled, "focus_object": focus_object, "focus_distance": focus_distance, "fstop": fstop}, group="cameras")

    @mcp.tool(name="camera_view")
    async def camera_view(
        name: str | None = None,
    ) -> dict[str, Any]:
        """Return camera framing metadata for visual verification."""
        return await call_blender(ctx, "camera_view", {"name": name}, group="cameras")

