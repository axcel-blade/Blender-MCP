"""Modifier MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="add_modifier")
    async def add_modifier(
        name: str,
        modifier_type: str,
        modifier_name: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a modifier to an object."""
        return await call_blender(ctx, "add_modifier", {"name": name, "modifier_type": modifier_type, "modifier_name": modifier_name, "settings": settings or {}}, group="modifiers")

    @mcp.tool(name="remove_modifier")
    async def remove_modifier(
        name: str,
        modifier_name: str,
    ) -> dict[str, Any]:
        """Remove a modifier from an object."""
        return await call_blender(ctx, "remove_modifier", {"name": name, "modifier_name": modifier_name}, group="modifiers")

    @mcp.tool(name="modify_modifier")
    async def modify_modifier(
        name: str,
        modifier_name: str,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        """Update modifier settings."""
        return await call_blender(ctx, "modify_modifier", {"name": name, "modifier_name": modifier_name, "settings": settings}, group="modifiers")

    @mcp.tool(name="apply_modifier")
    async def apply_modifier(
        name: str,
        modifier_name: str,
    ) -> dict[str, Any]:
        """Apply a modifier."""
        return await call_blender(ctx, "apply_modifier", {"name": name, "modifier_name": modifier_name}, group="modifiers")

    @mcp.tool(name="list_modifiers")
    async def list_modifiers(
        name: str,
    ) -> dict[str, Any]:
        """List modifiers on an object with settings."""
        return await call_blender(ctx, "list_modifiers", {"name": name}, group="modifiers")

