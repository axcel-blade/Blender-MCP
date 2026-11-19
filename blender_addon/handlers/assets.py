"""Asset import helpers that run inside Blender."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from . import command


@command("import_polyhaven_asset")
def import_polyhaven_asset(params: dict[str, Any]):
    import json

    import bpy

    asset_id = params["asset_id"]
    asset_type = params.get("asset_type") or "models"
    resolution = params.get("resolution") or "1k"
    info_url = f"https://api.polyhaven.com/files/{asset_id}"
    with urlopen(info_url, timeout=60) as resp:  # noqa: S310 — intentional provider API
        files = json.loads(resp.read().decode("utf-8"))

    download_url = None
    if asset_type in {"hdris", "hdri"}:
        # Prefer HDR/EXR
        for fmt in ("hdr", "exr"):
            node = files.get(fmt) or {}
            res_node = node.get(resolution) or next(iter(node.values()), None)
            if isinstance(res_node, dict):
                download_url = res_node.get("url")
                if download_url:
                    break
    elif asset_type in {"textures", "texture"}:
        # Prefer blend or zip map packages when available — fall back to first file URL
        for fmt, node in files.items():
            if isinstance(node, dict):
                res_node = node.get(resolution) or next(iter(node.values()), {})
                if isinstance(res_node, dict) and res_node.get("url"):
                    download_url = res_node["url"]
                    break
    else:
        blend = files.get("blend") or {}
        res_node = blend.get(resolution) or next(iter(blend.values()), {})
        if isinstance(res_node, dict):
            download_url = res_node.get("url")

    if not download_url:
        raise ValueError(f"Could not resolve Poly Haven download URL for {asset_id}")

    dest = Path(tempfile.gettempdir()) / f"polyhaven_{asset_id}{Path(download_url).suffix or '.bin'}"
    with urlopen(download_url, timeout=120) as resp, dest.open("wb") as out:  # noqa: S310
        out.write(resp.read())

    before = set(bpy.data.objects.keys())
    if dest.suffix.lower() == ".blend":
        with bpy.data.libraries.load(str(dest)) as (data_from, data_to):
            data_to.objects = data_from.objects
        for obj in data_to.objects:
            if obj is not None:
                bpy.context.scene.collection.objects.link(obj)
    elif dest.suffix.lower() in {".hdr", ".exr"}:
        world = bpy.data.worlds.new(f"PH_{asset_id}")
        world.use_nodes = True
        nt = world.node_tree
        bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(str(dest))
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bpy.context.scene.world = world
    else:
        from .import_export import import_asset

        return import_asset({"path": str(dest)})

    imported = sorted(set(bpy.data.objects.keys()) - before)
    for obj_name in imported:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj["polyhaven_id"] = asset_id
            obj["polyhaven_licence"] = "CC0"
    return {
        "asset_id": asset_id,
        "path": str(dest),
        "imported_objects": imported,
        "source": "polyhaven",
        "licence": "CC0",
    }
