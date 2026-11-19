"""Sketchfab provider (requires API key)."""

from __future__ import annotations

from typing import Any

import httpx

from blender_mcp.exceptions import AssetDownloadFailedError, BlenderMCPError, ErrorCode
from blender_mcp.providers.base import AssetProvider

API = "https://api.sketchfab.com/v3"


class SketchfabProvider(AssetProvider):
    name = "sketchfab"

    def __init__(self, api_key: str = "", enabled: bool = False) -> None:
        self.api_key = api_key
        self.enabled = enabled

    def credential_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "configured": bool(self.api_key),
        }

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise BlenderMCPError(
                "Sketchfab API key missing. Set BLENDER_MCP_SKETCHFAB_API_KEY.",
                code=ErrorCode.PERMISSION_DENIED,
            )
        return {"Authorization": f"Token {self.api_key}"}

    async def search(
        self, query: str, *, asset_type: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            raise BlenderMCPError("Sketchfab provider is disabled", code=ErrorCode.PERMISSION_DENIED)
        params = {"type": "models", "q": query, "downloadable": "true", "count": str(limit)}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API}/search", params=params, headers=self._headers())
            response.raise_for_status()
            payload = response.json()
        results = []
        for item in payload.get("results", [])[:limit]:
            results.append(
                {
                    "id": item.get("uid"),
                    "name": item.get("name"),
                    "url": (item.get("viewerUrl") or item.get("uri")),
                    "licence": (item.get("license") or {}).get("label"),
                    "source": self.name,
                }
            )
        return results

    async def download(
        self, asset_id: str, *, asset_type: str | None = None, resolution: str = "1k"
    ) -> dict[str, Any]:
        if not self.enabled:
            raise BlenderMCPError("Sketchfab provider is disabled", code=ErrorCode.PERMISSION_DENIED)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{API}/models/{asset_id}/download", headers=self._headers()
                )
                response.raise_for_status()
                return {"id": asset_id, "download": response.json(), "source": self.name}
        except httpx.HTTPError as exc:
            raise AssetDownloadFailedError(f"Sketchfab download failed: {exc}") from exc
