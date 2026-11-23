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


# The "core" profile: a handful of high-leverage tools. execute_blender_code covers the
# full bpy API, so narrow wrappers mostly add tool-selection noise and context cost.
CORE_TOOLS = frozenset(
    {
        "get_addon_status",
        "get_guide",
        "get_scene_info",
        "get_object_info",
        "search_scene",
        "execute_blender_code",
        "lookup_api",
        "look",
        "search_assets",
        "import_external_asset",
        "generate_3d",
        "get_generation_status",
        "blender_mcp_version",
        "open_blender",
        "close_blender",
        "blend_file",
    }
)


def apply_tool_profile(mcp: FastMCP, profile: str) -> None:
    """Drop every non-core tool when running the core profile."""
    if profile != "core":
        return
    for tool in list(mcp._tool_manager.list_tools()):  # noqa: SLF001
        if tool.name not in CORE_TOOLS:
            mcp.remove_tool(tool.name)


def register_all_tools(mcp: FastMCP, ctx: AppContext) -> None:
    from blender_mcp.tools import (
        animation,
        app,
        assets,
        cameras,
        collections,
        environment,
        files,
        generation,
        geometry_nodes,
        import_export,
        lighting,
        materials,
        meshes,
        modeling,
        modifiers,
        objects,
        physics,
        post,
        production,
        render_config,
        rendering,
        rigging,
        scene,
        screenshots,
        scripting,
        sculpting,
        status,
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
        generation,
        import_export,
        collections,
        screenshots,
        scripting,
        status,
        app,
        files,
        # Capability expansion (full profile only).
        modeling,
        sculpting,
        rigging,
        physics,
        render_config,
        post,
        environment,
        production,
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


async def call_blender_paths(
    ctx: AppContext,
    command: str,
    params: dict[str, Any],
    *,
    group: str,
    path_keys: tuple[str, ...] = ("path",),
    must_exist: bool = True,
) -> dict[str, Any]:
    """Like ``call_blender`` but first checks file paths against ``allowed_directories``.

    Values may be a string or a list/dict of strings (e.g. a PBR ``maps`` dict).
    """
    from blender_mcp.security.validation import validate_path
    from blender_mcp.utils.results import fail_from_exception

    dirs = ctx.settings.allowed_directories
    try:
        for key in path_keys:
            value = params.get(key)
            if not value:
                continue
            values = (
                value.values()
                if isinstance(value, dict)
                else value
                if isinstance(value, list)
                else [value]
            )
            for item in values:
                validate_path(str(item), allowed_directories=dirs, must_exist=must_exist)
    except Exception as exc:  # noqa: BLE001
        return fail_from_exception(exc)
    return await call_blender(ctx, command, params, group=group)


def forward_params(local_vars: dict[str, Any]) -> dict[str, Any]:
    """Turn a tool function's ``locals()`` into bridge params (drops ctx and unset values)."""
    return {k: v for k, v in local_vars.items() if k not in {"ctx", "mcp"} and v is not None}
