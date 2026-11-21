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

    dest = (
        Path(tempfile.gettempdir()) / f"polyhaven_{asset_id}{Path(download_url).suffix or '.bin'}"
    )
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


def _world_bbox(objs) -> dict[str, list[float]] | None:
    from mathutils import Vector

    pts = []
    for obj in objs:
        if obj.type in {"MESH", "CURVE", "SURFACE", "FONT", "META"}:
            pts.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)
    if not pts:
        return None
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    return {"min": mn, "max": mx, "size": [mx[i] - mn[i] for i in range(3)]}


def _fit_and_ground(objs, target_size: float | None, ground: bool) -> dict | None:
    """Uniformly scale imported roots so the longest side == target_size, then sit on z=0."""
    import bpy

    roots = [o for o in objs if o.parent is None or o.parent not in objs]
    bbox = _world_bbox(objs)
    if bbox and target_size and target_size > 0:
        longest = max(bbox["size"]) or 1.0
        factor = target_size / longest
        for root in roots:
            root.scale = [s * factor for s in root.scale]
            root.location = [v * factor for v in root.location]
        bpy.context.view_layer.update()
        bbox = _world_bbox(objs)
    if bbox and ground:
        dz = -bbox["min"][2]
        for root in roots:
            root.location.z += dz
        bpy.context.view_layer.update()
        bbox = _world_bbox(objs)
    return bbox


def _texture_material(name: str, maps: dict[str, str]):
    import bpy

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def tex(role: str, non_color: bool):
        img = bpy.data.images.load(maps[role], check_existing=True)
        if non_color:
            img.colorspace_settings.is_data = True
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        return node

    if "base_color" in maps:
        nt.links.new(tex("base_color", False).outputs["Color"], bsdf.inputs["Base Color"])
    if "roughness" in maps:
        nt.links.new(tex("roughness", True).outputs["Color"], bsdf.inputs["Roughness"])
    if "metallic" in maps:
        nt.links.new(tex("metallic", True).outputs["Color"], bsdf.inputs["Metallic"])
    if "normal" in maps:
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tex("normal", True).outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


@command("import_local_asset")
def import_local_asset(params: dict[str, Any]):
    """Import an asset the MCP server already downloaded to a local path."""
    import bpy

    kind = params.get("kind") or "model"
    source = params.get("source") or "unknown"
    asset_id = str(params.get("asset_id") or "")
    licence = params.get("licence")

    if kind == "hdri":
        world = bpy.data.worlds.new(f"{source}_{asset_id}")
        world.use_nodes = True
        nt = world.node_tree
        bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(params["path"], check_existing=True)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bpy.context.scene.world = world
        return {"kind": "hdri", "world": world.name, "source": source, "licence": licence}

    if kind == "texture":
        mat = _texture_material(f"{source}_{asset_id}", params.get("maps") or {})
        applied = []
        for name in params.get("apply_to") or []:
            obj = bpy.data.objects.get(name)
            if obj is not None and hasattr(obj.data, "materials"):
                obj.data.materials.clear()
                obj.data.materials.append(mat)
                applied.append(name)
        return {"kind": "texture", "material": mat.name, "applied_to": applied, "source": source}

    from .import_export import import_asset

    result = import_asset({"path": params["path"], "collection": params.get("collection")})
    objs = [bpy.data.objects[n] for n in result["imported_objects"] if n in bpy.data.objects]
    for obj in objs:
        obj["mcp_source"] = source
        obj["mcp_asset_id"] = asset_id
        if licence:
            obj["mcp_licence"] = str(licence)
    bbox = _fit_and_ground(objs, params.get("target_size"), bool(params.get("ground", True)))
    return {
        "kind": "model",
        "imported_objects": result["imported_objects"],
        "world_bounding_box": bbox,
        "source": source,
        "licence": licence,
    }
