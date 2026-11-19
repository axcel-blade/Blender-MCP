"""Geometry Nodes MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="create_geometry_nodes_modifier")
    async def create_geometry_nodes_modifier(
        name: str,
        group_name: str | None = None,
    ) -> dict[str, Any]:
        """Add a Geometry Nodes modifier."""
        return await call_blender(
            ctx,
            "create_geometry_nodes_modifier",
            {"name": name, "group_name": group_name},
            group="geometry_nodes",
        )

    @mcp.tool(name="create_node_group")
    async def create_node_group(
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a geometry node group."""
        return await call_blender(ctx, "create_node_group", {"name": name}, group="geometry_nodes")

    @mcp.tool(name="add_geometry_node")
    async def add_geometry_node(
        group_name: str,
        node_type: str,
        node_name: str | None = None,
    ) -> dict[str, Any]:
        """Add a node to a geometry node group."""
        return await call_blender(
            ctx,
            "add_geometry_node",
            {"group_name": group_name, "node_type": node_type, "node_name": node_name},
            group="geometry_nodes",
        )

    @mcp.tool(name="connect_geometry_nodes")
    async def connect_geometry_nodes(
        group_name: str,
        from_node: str,
        from_socket: str,
        to_node: str,
        to_socket: str,
    ) -> dict[str, Any]:
        """Connect two geometry nodes."""
        return await call_blender(
            ctx,
            "connect_geometry_nodes",
            {
                "group_name": group_name,
                "from_node": from_node,
                "from_socket": from_socket,
                "to_node": to_node,
                "to_socket": to_socket,
            },
            group="geometry_nodes",
        )

    @mcp.tool(name="set_geometry_node_input")
    async def set_geometry_node_input(
        group_name: str,
        node_name: str,
        input_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """Set a geometry node input value."""
        return await call_blender(
            ctx,
            "set_geometry_node_input",
            {
                "group_name": group_name,
                "node_name": node_name,
                "input_name": input_name,
                "value": value,
            },
            group="geometry_nodes",
        )

    @mcp.tool(name="inspect_node_group")
    async def inspect_node_group(
        group_name: str,
    ) -> dict[str, Any]:
        """Inspect a node group structure."""
        return await call_blender(
            ctx, "inspect_node_group", {"group_name": group_name}, group="geometry_nodes"
        )

    @mcp.tool(name="list_geometry_node_types")
    async def list_geometry_node_types() -> dict[str, Any]:
        """List available geometry node type identifiers."""
        return await call_blender(ctx, "list_geometry_node_types", {}, group="geometry_nodes")

    @mcp.tool(name="get_node_socket_info")
    async def get_node_socket_info(
        group_name: str,
        node_name: str,
    ) -> dict[str, Any]:
        """Get socket schema for a node."""
        return await call_blender(
            ctx,
            "get_node_socket_info",
            {"group_name": group_name, "node_name": node_name},
            group="geometry_nodes",
        )
