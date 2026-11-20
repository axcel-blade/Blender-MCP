"""MCP server entrypoints."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from blender_mcp import __version__
from blender_mcp.config import Settings, load_settings
from blender_mcp.logging_config import setup_logging
from blender_mcp.prompts.registry import register_prompts
from blender_mcp.protocol.client import BlenderBridgeClient
from blender_mcp.resources.registry import register_resources
from blender_mcp.tools.registry import AppContext, register_all_tools

INSTRUCTIONS = """
You are connected to Blender through Blender MCP.

Start with get_addon_status (versions, warnings, enabled libraries and generators).
Short guides are available via get_guide (bpy, materials, scene).
Screenshot tools return real images: look at them to check your work.
Assets: search_assets, then import_external_asset (Poly Haven, Sketchfab, Poly Pizza).
generate_3d makes ONE new model from text/image (1-3 min, may cost a credit).

Visual verification workflow (required when screenshots are available):
1. Inspect the scene before changing user content.
2. Prefer creating a dedicated collection for new work.
3. Perform modeling/material/lighting/camera operations with meaningful names.
4. Capture a viewport or camera screenshot.
5. Inspect the image, fix issues, and capture again.
6. Only then report completion.

Do not delete existing user objects unless explicitly asked.
Prefer dedicated tools over execute_blender_code.
execute_blender_code is powerful and not a secure sandbox.
""".strip()


def create_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or load_settings()
    setup_logging(settings.log_level, settings.log_file)

    bridge = BlenderBridgeClient(settings.bridge())
    ctx = AppContext(settings=settings, bridge=bridge)

    mcp = FastMCP(
        name="Blender MCP",
        instructions=INSTRUCTIONS,
    )

    register_all_tools(mcp, ctx)
    register_resources(mcp, ctx)
    register_prompts(mcp)

    @mcp.tool(name="blender_mcp_version")
    async def blender_mcp_version() -> dict:
        """Return Blender MCP server version and bridge configuration (no secrets)."""
        return {
            "success": True,
            "result": {
                "version": __version__,
                "host": settings.host,
                "port": settings.port,
                "safe_execution_mode": settings.safe_execution_mode,
                "script_permission": str(settings.script_permission),
                "tool_groups": settings.tool_groups.model_dump(),
                "auth_configured": bool(settings.auth_token),
            },
        }

    return mcp


def main() -> None:
    """Stdio MCP entrypoint used by the console script."""
    settings = load_settings()
    mcp = create_server(settings)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
