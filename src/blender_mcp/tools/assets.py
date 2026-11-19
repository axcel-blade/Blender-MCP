"""Asset provider MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.exceptions import BlenderMCPError
from blender_mcp.providers.ai_3d import provider_statuses
from blender_mcp.providers.polyhaven import PolyHavenProvider
from blender_mcp.providers.polypizza import PolyPizzaProvider
from blender_mcp.providers.sketchfab import SketchfabProvider
from blender_mcp.security.permissions import require_tool_group
from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.utils.results import fail_from_exception, ok


def register(mcp: FastMCP, ctx: AppContext) -> None:
    def _providers():
        p = ctx.settings.providers()
        return {
            "polyhaven": PolyHavenProvider(enabled=p.polyhaven),
            "sketchfab": SketchfabProvider(api_key=p.sketchfab_api_key, enabled=p.sketchfab),
            "polypizza": PolyPizzaProvider(api_key=p.polypizza_api_key, enabled=p.polypizza),
        }

    @mcp.tool(name="search_assets")
    async def search_assets(
        source: str,
        query: str,
        asset_type: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search external asset providers (polyhaven, sketchfab, polypizza)."""
        try:
            require_tool_group(ctx.settings, "assets")
            providers = _providers()
            provider = providers.get(source.lower())
            if provider is None:
                raise BlenderMCPError(f"Unknown asset source: {source}")
            results = await provider.search(query, asset_type=asset_type, limit=limit)
            return ok(results)
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)

    @mcp.tool(name="import_external_asset")
    async def import_external_asset(
        source: str,
        asset_id: str,
        asset_type: str | None = None,
        resolution: str = "1k",
    ) -> dict[str, Any]:
        """Download metadata/URLs then ask Blender to import when a local path is available."""
        try:
            require_tool_group(ctx.settings, "assets")
            providers = _providers()
            provider = providers.get(source.lower())
            if provider is None:
                raise BlenderMCPError(f"Unknown asset source: {source}")
            download = await provider.download(
                asset_id, asset_type=asset_type, resolution=resolution
            )
            # Blender-side import for Poly Haven / others is handled via execute path when path known.
            # Return download info so the AI or a follow-up import_asset call can proceed.
            return ok(
                {
                    "download": download,
                    "next_step": (
                        "Use import_asset with a downloaded local path, or ask Blender to fetch "
                        "via execute_blender_code when trusted mode is enabled."
                    ),
                }
            )
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)

    @mcp.tool(name="list_asset_providers")
    async def list_asset_providers() -> dict[str, Any]:
        """List configured asset providers and credential status (no secrets)."""
        try:
            require_tool_group(ctx.settings, "assets")
            p = ctx.settings.providers()
            statuses = [
                {"name": "polyhaven", "enabled": p.polyhaven, "configured": True, "licence": "CC0"},
                {
                    "name": "sketchfab",
                    "enabled": p.sketchfab,
                    "configured": bool(p.sketchfab_api_key),
                },
                {
                    "name": "polypizza",
                    "enabled": p.polypizza,
                    "configured": bool(p.polypizza_api_key),
                },
            ]
            statuses.extend(provider_statuses(ctx.settings))
            return ok(statuses)
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)

    # Keep a blender-forward alias used by some workflows
    @mcp.tool(name="import_polyhaven_via_blender")
    async def import_polyhaven_via_blender(
        asset_id: str,
        asset_type: str = "models",
        resolution: str = "1k",
    ) -> dict[str, Any]:
        """Ask Blender to import a Poly Haven asset by id (addon-side download)."""
        return await call_blender(
            ctx,
            "import_polyhaven_asset",
            {"asset_id": asset_id, "asset_type": asset_type, "resolution": resolution},
            group="assets",
        )
