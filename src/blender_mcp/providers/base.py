"""Base provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AssetProvider(ABC):
    name: str

    @abstractmethod
    async def search(
        self, query: str, *, asset_type: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def download(
        self, asset_id: str, *, asset_type: str | None = None, resolution: str = "1k"
    ) -> dict[str, Any]:
        raise NotImplementedError

    def credential_status(self) -> dict[str, Any]:
        return {"name": self.name, "configured": True}
