"""Poly Haven asset provider (CC0)."""

from __future__ import annotations

from typing import Any

import httpx

from blender_mcp.exceptions import AssetDownloadFailedError, BlenderMCPError, ErrorCode
from blender_mcp.providers.base import AssetProvider

API = "https://api.polyhaven.com"


class PolyHavenProvider(AssetProvider):
    name = "polyhaven"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    async def search(
        self, query: str, *, asset_type: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            raise BlenderMCPError("Poly Haven provider is disabled", code=ErrorCode.PERMISSION_DENIED)
        params: dict[str, str] = {}
        if asset_type:
            params["type"] = asset_type
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API}/assets", params=params)
            response.raise_for_status()
            data = response.json()
        query_l = query.lower()
        results: list[dict[str, Any]] = []
        for asset_id, meta in data.items():
            hay = " ".join(
                [
                    asset_id,
                    str(meta.get("name", "")),
                    " ".join(meta.get("tags", []) or []),
                    " ".join(meta.get("categories", []) or []),
                ]
            ).lower()
            if query_l not in hay and not all(part in hay for part in query_l.split()):
                continue
            results.append(
                {
                    "id": asset_id,
                    "name": meta.get("name", asset_id),
                    "type": meta.get("type"),
                    "url": f"https://polyhaven.com/a/{asset_id}",
                    "licence": "CC0",
                    "source": self.name,
                }
            )
            if len(results) >= limit:
                break
        return results

    async def download(
        self, asset_id: str, *, asset_type: str | None = None, resolution: str = "1k"
    ) -> dict[str, Any]:
        if not self.enabled:
            raise BlenderMCPError("Poly Haven provider is disabled", code=ErrorCode.PERMISSION_DENIED)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                info = await client.get(f"{API}/info/{asset_id}")
                info.raise_for_status()
                files = await client.get(f"{API}/files/{asset_id}")
                files.raise_for_status()
                return {
                    "id": asset_id,
                    "info": info.json(),
                    "files": files.json(),
                    "resolution": resolution,
                    "source": self.name,
                    "note": "File URLs resolved; Blender addon performs the actual import.",
                }
        except httpx.HTTPError as exc:
            raise AssetDownloadFailedError(f"Poly Haven download failed: {exc}") from exc
