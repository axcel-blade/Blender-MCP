"""Download provider assets to local files so the Blender addon can import them.

The MCP server and Blender normally run on the same machine, so the server fetches the
files (with size limits and path-traversal checks) and hands Blender local paths.
"""

from __future__ import annotations

import re
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

from blender_mcp.exceptions import AssetDownloadFailedError, InvalidParameterError

MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")

# Poly Haven texture map names -> role used by the addon material builder.
POLYHAVEN_TEXTURE_MAPS = {
    "Diffuse": "base_color",
    "nor_gl": "normal",
    "Rough": "roughness",
    "Metal": "metallic",
    "Displacement": "displacement",
    "AO": "ao",
}


def asset_dir(source: str, asset_id: str, root: Path | None = None) -> Path:
    base = root or Path(tempfile.gettempdir()) / "blender_mcp_assets"
    path = base / f"{source}_{_SAFE_ID.sub('_', asset_id)[:80]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_join(root: Path, relative: str) -> Path:
    """Join a provider-supplied relative path under ``root``, rejecting traversal."""
    rel = PurePosixPath(relative.replace("\\", "/"))
    if rel.is_absolute() or ".." in rel.parts or not rel.parts or ":" in rel.parts[0]:
        raise InvalidParameterError(f"Unsafe path in asset package: {relative!r}")
    target = (root / Path(*rel.parts)).resolve()
    if not target.is_relative_to(root.resolve()):
        raise InvalidParameterError(f"Unsafe path in asset package: {relative!r}")
    return target


async def fetch_file(
    client: httpx.AsyncClient,
    url: str,
    dest: Path,
    *,
    headers: dict[str, str] | None = None,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> Path:
    if not url.startswith("https://"):
        raise AssetDownloadFailedError(f"Refusing non-HTTPS download URL: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        async with client.stream("GET", url, headers=headers, follow_redirects=True) as resp:
            resp.raise_for_status()
            with dest.open("wb") as out:
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise AssetDownloadFailedError(
                            f"Download exceeds {max_bytes // (1024 * 1024)} MB limit"
                        )
                    out.write(chunk)
    except httpx.HTTPError as exc:
        dest.unlink(missing_ok=True)
        raise AssetDownloadFailedError(f"Download failed: {exc}") from exc
    except AssetDownloadFailedError:
        dest.unlink(missing_ok=True)
        raise
    return dest


def extract_zip(archive: Path, root: Path, max_bytes: int = MAX_DOWNLOAD_BYTES * 2) -> Path:
    """Extract a zip safely (no zip-slip, bounded size) and return the model file inside."""
    with zipfile.ZipFile(archive) as zf:
        if sum(info.file_size for info in zf.infolist()) > max_bytes:
            raise AssetDownloadFailedError("Archive too large when extracted")
        for info in zf.infolist():
            target = safe_join(root, info.filename)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                dst.write(src.read())
    return find_model_file(root)


def find_model_file(root: Path) -> Path:
    for pattern in ("*.glb", "*.gltf", "*.fbx", "*.obj", "*.blend"):
        found = sorted(root.rglob(pattern))
        if found:
            return found[0]
    raise AssetDownloadFailedError("No importable model file found in download")


def _pick_res(node: dict[str, Any], resolution: str) -> dict[str, Any] | None:
    if not isinstance(node, dict) or not node:
        return None
    if resolution in node:
        return node[resolution]

    # Fall back to the smallest available resolution (e.g. "1k" < "2k").
    def _key(k: str) -> int:
        digits = "".join(ch for ch in k if ch.isdigit())
        return int(digits) if digits else 9999

    return node[sorted(node, key=_key)[0]]


POLYHAVEN_TYPES = {0: "hdris", 1: "textures", 2: "models"}


def normalize_polyhaven_type(asset_type: str | None) -> str | None:
    if not asset_type:
        return None
    t = asset_type.lower().rstrip("s")
    return {"hdri": "hdris", "texture": "textures", "model": "models"}.get(t)


async def download_polyhaven(
    asset_id: str, asset_type: str | None, resolution: str, root: Path | None = None
) -> dict[str, Any]:
    api = "https://api.polyhaven.com"
    kind = normalize_polyhaven_type(asset_type)
    async with httpx.AsyncClient(timeout=120.0) as client:
        if kind is None:
            info = (await client.get(f"{api}/info/{asset_id}")).raise_for_status().json()
            kind = POLYHAVEN_TYPES.get(info.get("type"), "models")
        files = (await client.get(f"{api}/files/{asset_id}")).raise_for_status().json()
        out = asset_dir("polyhaven", asset_id, root)

        if kind == "hdris":
            res = _pick_res(files.get("hdri", {}), resolution) or {}
            entry = res.get("hdr") or res.get("exr")
            if not entry:
                raise AssetDownloadFailedError(f"No HDRI file for {asset_id}")
            path = await fetch_file(
                client, entry["url"], out / f"{asset_id}{Path(entry['url']).suffix}"
            )
            return {"kind": "hdri", "path": str(path)}

        if kind == "textures":
            maps: dict[str, str] = {}
            for map_name, role in POLYHAVEN_TEXTURE_MAPS.items():
                res = _pick_res(files.get(map_name, {}), resolution) or {}
                entry = res.get("jpg") or res.get("png")
                if entry:
                    dest = out / f"{asset_id}_{map_name}{Path(entry['url']).suffix}"
                    maps[role] = str(await fetch_file(client, entry["url"], dest))
            if "base_color" not in maps:
                raise AssetDownloadFailedError(f"No diffuse map for texture {asset_id}")
            return {"kind": "texture", "maps": maps}

        res = _pick_res(files.get("gltf", {}), resolution) or {}
        gltf = res.get("gltf")
        if not gltf:
            raise AssetDownloadFailedError(f"No glTF package for model {asset_id}")
        main = await fetch_file(client, gltf["url"], out / f"{asset_id}.gltf")
        for rel, meta in (gltf.get("include") or {}).items():
            await fetch_file(client, meta["url"], safe_join(out, rel))
        return {"kind": "model", "path": str(main)}


async def download_sketchfab(
    asset_id: str, api_key: str, root: Path | None = None
) -> dict[str, Any]:
    headers = {"Authorization": f"Token {api_key}"}
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(
            f"https://api.sketchfab.com/v3/models/{asset_id}/download", headers=headers
        )
        if resp.status_code in (401, 403):
            raise AssetDownloadFailedError(
                "Sketchfab refused the download (check API key / model is downloadable)"
            )
        payload = resp.raise_for_status().json()
        out = asset_dir("sketchfab", asset_id, root)
        # Signed URLs: do not forward the API token to the storage host.
        if payload.get("glb", {}).get("url"):
            path = await fetch_file(client, payload["glb"]["url"], out / f"{asset_id}.glb")
            return {"kind": "model", "path": str(path)}
        url = (payload.get("gltf") or {}).get("url")
        if not url:
            raise AssetDownloadFailedError("Sketchfab returned no glTF/GLB download")
        archive = await fetch_file(client, url, out / f"{asset_id}.zip")
        model = extract_zip(archive, out / "extracted")
        return {"kind": "model", "path": str(model)}


async def download_polypizza(
    asset_id: str, api_key: str, root: Path | None = None
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        meta = (
            (
                await client.get(
                    f"https://api.poly.pizza/v1/model/{asset_id}", headers={"x-auth-token": api_key}
                )
            )
            .raise_for_status()
            .json()
        )
        url = meta.get("Download") or meta.get("download")
        if not url:
            raise AssetDownloadFailedError("Poly Pizza returned no download URL")
        out = asset_dir("polypizza", asset_id, root)
        path = await fetch_file(client, url, out / f"{asset_id}.glb")
        return {
            "kind": "model",
            "path": str(path),
            "licence": meta.get("Licence") or meta.get("license"),
            "author": (meta.get("Creator") or {}).get("Username"),
        }
