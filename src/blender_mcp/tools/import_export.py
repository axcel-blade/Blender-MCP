"""Import/export MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="import_asset")
    async def import_asset(
        path: str,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Import a 3D asset (FBX/OBJ/STL/GLTF/GLB/USD/BLEND)."""
        return await call_blender(ctx, "import_asset", {"path": path, "collection": collection}, group="import_export")

    @mcp.tool(name="export_asset")
    async def export_asset(
        path: str,
        objects: list[str] | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Export selected or named objects."""
        return await call_blender(ctx, "export_asset", {"path": path, "objects": objects, "overwrite": overwrite}, group="import_export")

    @mcp.tool(name="export_selected_objects")
    async def export_selected_objects(
        path: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Export currently selected objects."""
        return await call_blender(ctx, "export_selected_objects", {"path": path, "overwrite": overwrite}, group="import_export")

    @mcp.tool(name="export_scene")
    async def export_scene(
        path: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Export the full scene."""
        return await call_blender(ctx, "export_scene", {"path": path, "overwrite": overwrite}, group="import_export")

    @mcp.tool(name="save_blend_file")
    async def save_blend_file(
        path: str | None = None,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        """Save the current .blend file."""
        return await call_blender(ctx, "save_blend_file", {"path": path, "overwrite": overwrite}, group="import_export")

    @mcp.tool(name="save_as")
    async def save_as(
        path: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Save the blend file to a new path."""
        return await call_blender(ctx, "save_as", {"path": path, "overwrite": overwrite}, group="import_export")

    @mcp.tool(name="open_blend_file")
    async def open_blend_file(
        path: str,
    ) -> dict[str, Any]:
        """Open a .blend file."""
        return await call_blender(ctx, "open_blend_file", {"path": path}, group="import_export")

    @mcp.tool(name="get_project_path")
    async def get_project_path(
    
    ) -> dict[str, Any]:
        """Get the current blend file path."""
        return await call_blender(ctx, "get_project_path", {}, group="import_export")

