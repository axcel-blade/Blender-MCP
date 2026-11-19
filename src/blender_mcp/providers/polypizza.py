"""Poly Pizza provider (requires API key)."""

from __future__ import annotations

from typing import Any

import httpx

from blender_mcp.exceptions import AssetDownloadFailedError, BlenderMCPError, ErrorCode
from blender_mcp.providers.base import AssetProvider

API = "https://api.poly.pizza/v1"


class PolyPizzaProvider(AssetProvider):
    name = "polypizza"

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
                "Poly Pizza API key missing. Set BLENDER_MCP_POLYPIZZA_API_KEY.",
                code=ErrorCode.PERMISSION_DENIED,
            )
        return {"x-auth-token": self.api_key}

    async def search(
        self, query: str, *, asset_type: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            raise BlenderMCPError("Poly Pizza provider is disabled", code=ErrorCode.PERMISSION_DENIED)
        params = {"search": query, "limit": str(limit)}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API}/search", params=params, headers=self._headers())
            response.raise_for_status()
            payload = response.json()
        results = []
        for item in (payload if isinstance(payload, list) else payload.get("results", []))[:limit]:
            results.append(
                {
                    "id": item.get("ID") or item.get("id"),
                    "name": item.get("Title") or item.get("title") or item.get("name"),
                    "licence": item.get("Licence") or item.get("license"),
                    "triangles": item.get("TriangleCount") or item.get("triangles"),
                    "source": self.name,
                }
            )
        return results

    async def download(
        self, asset_id: str, *, asset_type: str | None = None, resolution: str = "1k"
    ) -> dict[str, Any]:
        if not self.enabled:
            raise BlenderMCPError("Poly Pizza provider is disabled", code=ErrorCode.PERMISSION_DENIED)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(f"{API}/model/{asset_id}", headers=self._headers())
                response.raise_for_status()
                return {"id": asset_id, "model": response.json(), "source": self.name}
        except httpx.HTTPError as exc:
            raise AssetDownloadFailedError(f"Poly Pizza download failed: {exc}") from exc
