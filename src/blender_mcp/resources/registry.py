"""Register MCP resources."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from blender_mcp.tools.registry import AppContext


def register_resources(mcp: FastMCP, ctx: AppContext) -> None:
    async def _fetch(command: str) -> str:
        from blender_mcp.exceptions import BlenderMCPError

        try:
            result = await ctx.bridge.send_command(command, {})
            return json.dumps(result, indent=2, default=str)
        except BlenderMCPError as exc:
            return json.dumps(exc.to_dict(), indent=2)

    @mcp.resource("blender://scene/summary")
    async def scene_summary() -> str:
        """Current Blender scene summary."""
        return await _fetch("get_scene_summary")

    @mcp.resource("blender://scene/objects")
    async def scene_objects() -> str:
        """Objects in the current scene."""
        return await _fetch("get_objects")

    @mcp.resource("blender://scene/hierarchy")
    async def scene_hierarchy() -> str:
        """Scene collection hierarchy."""
        return await _fetch("get_scene_hierarchy")

    @mcp.resource("blender://scene/materials")
    async def scene_materials() -> str:
        """Materials in the blend file."""
        return await _fetch("get_materials")

    @mcp.resource("blender://scene/cameras")
    async def scene_cameras() -> str:
        """Cameras in the scene."""
        return await _fetch("get_camera_info")

    @mcp.resource("blender://scene/lights")
    async def scene_lights() -> str:
        """Lights in the scene."""
        return await _fetch("get_lights")

    @mcp.resource("blender://scene/render-settings")
    async def render_settings() -> str:
        """Current render settings."""
        return await _fetch("get_render_settings")

    @mcp.resource("blender://blender/version")
    async def blender_version() -> str:
        """Blender and addon version information."""
        return await _fetch("diagnose_blender_connection")

    @mcp.resource("blender://connection/status")
    async def connection_status() -> str:
        """Bridge connection status."""
        status = await ctx.bridge.diagnose()
        return json.dumps(status, indent=2, default=str)

    @mcp.resource("blender://documentation/bpy")
    async def bpy_docs() -> str:
        """High-level bpy usage notes for AI operators."""
        return (
            "# Blender bpy guidance\\n"
            "- Prefer dedicated MCP tools over execute_blender_code.\\n"
            "- Look up shader nodes by type, not localized names.\\n"
            "- Run operators from OBJECT mode unless a tool says otherwise.\\n"
            "- Use collections to organize new work; avoid deleting user content.\\n"
            "- Always capture a viewport screenshot before claiming completion.\\n"
        )
