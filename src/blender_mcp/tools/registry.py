"""Register all MCP tools onto a FastMCP instance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from blender_mcp.config import Settings
    from blender_mcp.protocol.client import BlenderBridgeClient


class AppContext:
    """Shared runtime context for tools."""

    def __init__(self, settings: Settings, bridge: BlenderBridgeClient) -> None:
        self.settings = settings
        self.bridge = bridge


def register_all_tools(mcp: FastMCP, ctx: AppContext) -> None:
    from blender_mcp.tools import (
        animation,
        assets,
        cameras,
        collections,
        geometry_nodes,
        import_export,
        lighting,
        materials,
        meshes,
        modifiers,
        objects,
        rendering,
        scene,
        screenshots,
        scripting,
    )

    modules = [
        scene,
        objects,
        meshes,
        modifiers,
        materials,
        geometry_nodes,
        cameras,
        lighting,
        rendering,
        animation,
        assets,
        import_export,
        collections,
        screenshots,
        scripting,
    ]
    for module in modules:
        module.register(mcp, ctx)


async def call_blender(
    ctx: AppContext,
    command: str,
    params: dict[str, Any] | None = None,
    *,
    group: str | None = None,
) -> dict[str, Any]:
    from blender_mcp.exceptions import BlenderMCPError
    from blender_mcp.security.permissions import require_tool_group
    from blender_mcp.utils.results import fail_from_exception

    try:
        if group:
            require_tool_group(ctx.settings, group)
        return await ctx.bridge.send_command(command, params or {})
    except BlenderMCPError as exc:
        return fail_from_exception(exc)
    except Exception as exc:  # noqa: BLE001
        return fail_from_exception(exc)
