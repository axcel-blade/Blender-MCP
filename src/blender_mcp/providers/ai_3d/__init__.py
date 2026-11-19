"""Optional AI 3D generation providers (Meshy, Tripo, Rodin, Hunyuan3D)."""

from __future__ import annotations

from typing import Any


def provider_statuses(settings: Any) -> list[dict[str, Any]]:
    providers = settings.providers()
    return [
        {
            "name": "meshy",
            "enabled": providers.meshy,
            "configured": bool(providers.meshy_api_key),
            "optional": True,
        },
        {
            "name": "tripo",
            "enabled": providers.tripo,
            "configured": bool(providers.tripo_api_key),
            "optional": True,
        },
        {
            "name": "rodin",
            "enabled": providers.rodin,
            "configured": bool(providers.rodin_api_key),
            "optional": True,
        },
        {
            "name": "hunyuan3d",
            "enabled": providers.hunyuan3d,
            "configured": bool(providers.hunyuan_secret_id and providers.hunyuan_secret_key),
            "optional": True,
        },
    ]
