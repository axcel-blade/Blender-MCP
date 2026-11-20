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
        query: str,
        source: str = "polyhaven",
        asset_type: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search an asset library. source: polyhaven (free HDRIs, textures, models;
        default), sketchfab or polypizza (need API keys; see get_addon_status).
        asset_type for polyhaven: hdris, textures or models."""
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
        target_size: float | None = None,
        apply_to: list[str] | None = None,
        ground: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Download an asset from Poly Haven, Sketchfab or Poly Pizza and import it into Blender.

        - Models: imported, optionally scaled so the longest side equals ``target_size``
          (meters) and placed on the ground. The reply includes ``world_bounding_box``.
        - Poly Haven HDRIs (asset_type="hdris"): set as the world lighting.
        - Poly Haven textures (asset_type="textures"): a PBR material, applied to the
          objects named in ``apply_to``.
        """
        from blender_mcp.providers import downloads

        try:
            require_tool_group(ctx.settings, "assets")
            p = ctx.settings.providers()
            src = source.lower().replace(" ", "")
            if src == "polyhaven":
                if not p.polyhaven:
                    raise BlenderMCPError("Poly Haven provider is disabled")
                got = await downloads.download_polyhaven(asset_id, asset_type, resolution)
                got.setdefault("licence", "CC0")
            elif src == "sketchfab":
                if not (p.sketchfab and p.sketchfab_api_key):
                    raise BlenderMCPError("Sketchfab needs enabling and an API key")
                got = await downloads.download_sketchfab(asset_id, p.sketchfab_api_key)
            elif src == "polypizza":
                if not (p.polypizza and p.polypizza_api_key):
                    raise BlenderMCPError("Poly Pizza needs enabling and an API key")
                got = await downloads.download_polypizza(asset_id, p.polypizza_api_key)
            else:
                raise BlenderMCPError(f"Unknown asset source: {source}")
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)

        params = {
            **got,
            "source": src,
            "asset_id": asset_id,
            "target_size": target_size,
            "apply_to": apply_to or [],
            "ground": ground,
            "collection": collection,
        }
        return await call_blender(ctx, "import_local_asset", params, group="assets")

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
