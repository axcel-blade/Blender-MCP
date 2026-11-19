"""Collection MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="create_collection")
    async def create_collection(
        name: str,
        parent: str | None = None,
    ) -> dict[str, Any]:
        """Create a collection."""
        return await call_blender(
            ctx, "create_collection", {"name": name, "parent": parent}, group="collections"
        )

    @mcp.tool(name="delete_collection")
    async def delete_collection(
        name: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Delete a collection."""
        return await call_blender(
            ctx, "delete_collection", {"name": name, "confirmed": confirmed}, group="collections"
        )

    @mcp.tool(name="rename_collection")
    async def rename_collection(
        name: str,
        new_name: str,
    ) -> dict[str, Any]:
        """Rename a collection."""
        return await call_blender(
            ctx, "rename_collection", {"name": name, "new_name": new_name}, group="collections"
        )

    @mcp.tool(name="move_object_to_collection")
    async def move_object_to_collection(
        object_name: str,
        collection: str,
        exclusive: bool = True,
    ) -> dict[str, Any]:
        """Move an object into a collection."""
        return await call_blender(
            ctx,
            "move_object_to_collection",
            {"object_name": object_name, "collection": collection, "exclusive": exclusive},
            group="collections",
        )

    @mcp.tool(name="get_collection_info")
    async def get_collection_info(
        name: str,
    ) -> dict[str, Any]:
        """Get collection details."""
        return await call_blender(ctx, "get_collection_info", {"name": name}, group="collections")

    @mcp.tool(name="organize_scene")
    async def organize_scene(
        structure: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """Organize objects into logical collections."""
        return await call_blender(
            ctx, "organize_scene", {"structure": structure}, group="collections"
        )

    @mcp.tool(name="create_hierarchy")
    async def create_hierarchy(
        names: list[str],
    ) -> dict[str, Any]:
        """Create nested collections by path names."""
        return await call_blender(ctx, "create_hierarchy", {"names": names}, group="collections")
