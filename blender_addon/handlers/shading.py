"""Shader-node editing and procedural material presets (PBR, textures, normal/displacement)."""

from __future__ import annotations

from typing import Any

from ..utils.objects import get_object
from . import command


def _material(name: str, create: bool = False):
    import bpy

    mat = bpy.data.materials.get(name)
    if mat is None:
        if not create:
            raise ValueError(f"Material not found: {name}")
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    return mat


def _socket(sockets, key):
    if isinstance(key, int):
        return sockets[key]
    if key in sockets:
        return sockets[key]
    found = next(
        (s for s in sockets if s.identifier == key or s.name.lower() == str(key).lower()), None
    )
    if found is None:
        raise ValueError(f"Socket {key!r} not found; have {[s.name for s in sockets]}")
    return found


def _set(node, key, value) -> bool:
    """Set an input if this Blender has it (Principled names changed in 4.0)."""
    aliases = {
        "Emission Color": ["Emission Color", "Emission"],
        "Specular": ["Specular IOR Level", "Specular"],
        "Transmission": ["Transmission Weight", "Transmission"],
        "Subsurface": ["Subsurface Weight", "Subsurface"],
        "Coat": ["Coat Weight", "Clearcoat"],
        "Sheen": ["Sheen Weight", "Sheen"],
    }
    for name in aliases.get(key, [key]):
        if name in node.inputs:
            node.inputs[name].default_value = value
            return True
    return False


@command("add_shader_node")
def add_shader_node(params: dict[str, Any]):
    mat = _material(params["material"], create=bool(params.get("create_material")))
    node = mat.node_tree.nodes.new(params["node_type"])
    if params.get("name"):
        node.name = node.label = params["name"]
    if params.get("location"):
        node.location = params["location"]
    for key, value in (params.get("inputs") or {}).items():
        _socket(node.inputs, key).default_value = value
    for key, value in (params.get("properties") or {}).items():
        setattr(node, key, value)
    return {
        "material": mat.name,
        "node": node.name,
        "type": node.bl_idname,
        "inputs": [s.name for s in node.inputs],
        "outputs": [s.name for s in node.outputs],
    }


@command("connect_shader_nodes")
def connect_shader_nodes(params: dict[str, Any]):
    mat = _material(params["material"])
    nodes = mat.node_tree.nodes
    src, dst = nodes.get(params["from_node"]), nodes.get(params["to_node"])
    if src is None or dst is None:
        raise ValueError(f"Node not found; have {[n.name for n in nodes]}")
    link = mat.node_tree.links.new(
        _socket(src.outputs, params.get("from_socket", 0)),
        _socket(dst.inputs, params.get("to_socket", 0)),
    )
    return {
        "from": f"{src.name}.{link.from_socket.name}",
        "to": f"{dst.name}.{link.to_socket.name}",
    }


@command("set_shader_node_input")
def set_shader_node_input(params: dict[str, Any]):
    mat = _material(params["material"])
    node = mat.node_tree.nodes.get(params["node"])
    if node is None:
        raise ValueError(f"Node not found: {params['node']}")
    for key, value in (params.get("inputs") or {}).items():
        _socket(node.inputs, key).default_value = value
    for key, value in (params.get("properties") or {}).items():
        setattr(node, key, value)
    return {"material": mat.name, "node": node.name}


@command("remove_shader_node")
def remove_shader_node(params: dict[str, Any]):
    mat = _material(params["material"])
    node = mat.node_tree.nodes.get(params["node"])
    if node is None:
        raise ValueError(f"Node not found: {params['node']}")
    mat.node_tree.nodes.remove(node)
    return {"material": mat.name, "removed": params["node"]}


# (base color, metallic, roughness, extra principled inputs, procedural texture)
PRESETS: dict[str, tuple] = {
    "chrome": ((0.95, 0.95, 0.95), 1.0, 0.03, {}, None),
    "polished_metal": ((0.8, 0.8, 0.82), 1.0, 0.12, {}, None),
    "brushed_metal": ((0.7, 0.7, 0.72), 1.0, 0.35, {"Anisotropic": 0.8}, "brushed"),
    "gold": ((1.0, 0.77, 0.34), 1.0, 0.15, {}, None),
    "copper": ((0.95, 0.64, 0.54), 1.0, 0.2, {}, None),
    "rust": ((0.45, 0.2, 0.08), 0.3, 0.85, {}, "rust"),
    "glass": ((1, 1, 1), 0.0, 0.0, {"Transmission": 1.0, "IOR": 1.45}, None),
    "frosted_glass": ((0.95, 0.97, 1), 0.0, 0.35, {"Transmission": 1.0, "IOR": 1.45}, None),
    "water": ((0.8, 0.9, 1.0), 0.0, 0.02, {"Transmission": 1.0, "IOR": 1.333}, None),
    "plastic": ((0.8, 0.1, 0.1), 0.0, 0.35, {}, None),
    "glossy_plastic": ((0.1, 0.3, 0.8), 0.0, 0.1, {"Coat": 0.5}, None),
    "rubber": ((0.03, 0.03, 0.03), 0.0, 0.9, {}, None),
    "car_paint": ((0.6, 0.02, 0.02), 0.6, 0.3, {"Coat": 1.0}, None),
    "ceramic": ((0.95, 0.95, 0.92), 0.0, 0.08, {"Coat": 0.6}, None),
    "wood": ((0.45, 0.27, 0.12), 0.0, 0.5, {}, "wood"),
    "marble": ((0.92, 0.92, 0.9), 0.0, 0.15, {}, "marble"),
    "concrete": ((0.55, 0.55, 0.53), 0.0, 0.9, {}, "concrete"),
    "brick": ((0.55, 0.22, 0.15), 0.0, 0.85, {}, "brick"),
    "fabric": ((0.3, 0.35, 0.55), 0.0, 0.95, {"Sheen": 0.5}, "fabric"),
    "leather": ((0.25, 0.13, 0.06), 0.0, 0.55, {}, "leather"),
    "skin": ((0.8, 0.57, 0.45), 0.0, 0.45, {"Subsurface": 0.2}, None),
    "ground": ((0.25, 0.18, 0.12), 0.0, 0.95, {}, "concrete"),
    "grass": ((0.12, 0.35, 0.08), 0.0, 0.8, {}, "fabric"),
    "sand": ((0.82, 0.7, 0.5), 0.0, 0.9, {}, "concrete"),
    "snow": ((0.95, 0.96, 1.0), 0.0, 0.5, {"Subsurface": 0.3}, None),
    "rock": ((0.35, 0.33, 0.3), 0.0, 0.85, {}, "concrete"),
    "neon": ((0.0, 0.0, 0.0), 0.0, 0.5, {"Emission Strength": 15.0}, None),
    "hologram": ((0.1, 0.6, 1.0), 0.0, 0.2, {"Alpha": 0.3, "Emission Strength": 3.0}, None),
}


def _procedural(nt, bsdf, kind, color, scale):
    nodes, links = nt.nodes, nt.links
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    dark = tuple(c * 0.45 for c in color)
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*color, 1)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.2
    if kind == "wood":
        tex = nodes.new("ShaderNodeTexWave")
        tex.wave_type = "RINGS"
        tex.inputs["Distortion"].default_value = 6.0
        tex.inputs["Detail"].default_value = 3.0
        out = tex.outputs["Fac"]
    elif kind == "marble":
        tex = nodes.new("ShaderNodeTexWave")
        tex.inputs["Distortion"].default_value = 12.0
        tex.inputs["Detail"].default_value = 8.0
        ramp.color_ramp.elements[0].color = (0.35, 0.35, 0.38, 1)
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[1].position = 0.15
        out = tex.outputs["Fac"]
    elif kind == "brick":
        tex = nodes.new("ShaderNodeTexBrick")
        tex.inputs["Color1"].default_value = (*color, 1)
        tex.inputs["Color2"].default_value = (*dark, 1)
        tex.inputs["Mortar"].default_value = (0.6, 0.6, 0.58, 1)
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        nodes.remove(ramp)
        return
    elif kind == "brushed":
        tex = nodes.new("ShaderNodeTexNoise")
        mapping.inputs["Scale"].default_value = (scale * 200, scale, scale)
        tex.inputs["Detail"].default_value = 2
        out = tex.outputs["Fac"]
        ramp.color_ramp.elements[0].color = (*[c * 0.8 for c in color], 1)
    elif kind == "rust":
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Detail"].default_value = 12
        tex.inputs["Roughness"].default_value = 0.7
        ramp.color_ramp.elements[0].color = (0.15, 0.06, 0.02, 1)
        ramp.color_ramp.elements[1].color = (0.7, 0.35, 0.1, 1)
        out = tex.outputs["Fac"]
    elif kind in {"fabric", "leather"}:
        tex = nodes.new("ShaderNodeTexVoronoi" if kind == "leather" else "ShaderNodeTexWave")
        if kind == "fabric":
            tex.inputs["Scale"].default_value = 60
        else:
            tex.inputs["Scale"].default_value = 40
        out = tex.outputs[0] if kind == "fabric" else tex.outputs["Distance"]
        bump.inputs["Strength"].default_value = 0.3
    else:  # concrete & generic grunge
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 8
        tex.inputs["Detail"].default_value = 15
        out = tex.outputs["Fac"]
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    links.new(out, ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(out, bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


@command("create_procedural_material")
def create_procedural_material(params: dict[str, Any]):
    """Physically plausible material from a preset, optionally assigned to objects."""
    import bpy

    preset = (params.get("preset") or "plastic").lower()
    if preset not in PRESETS:
        raise ValueError(f"preset must be one of {sorted(PRESETS)}")
    color, metallic, rough, extra, proc = PRESETS[preset]
    if params.get("color"):
        color = tuple(params["color"][:3])
    name = params.get("name") or preset.replace("_", " ").title()
    mat = bpy.data.materials.get(name) if params.get("reuse", True) else None
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = float(
            params.get("roughness") if params.get("roughness") is not None else rough
        )
        for key, value in extra.items():
            _set(bsdf, key, value)
        if preset in {"neon", "hologram"}:
            _set(bsdf, "Emission Color", (*(params.get("color") or (0.1, 0.6, 1.0))[:3], 1))
        if "Alpha" in extra:
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "BLENDED"
            elif hasattr(mat, "blend_method"):
                mat.blend_method = "BLEND"
        if proc:
            _procedural(nt, bsdf, proc, color, float(params.get("texture_scale") or 1.0))
        mat.diffuse_color = (*color, 1)
        mat.metallic, mat.roughness = metallic, rough
    assigned = []
    for obj_name in params.get("assign_to") or []:
        obj = get_object(obj_name)
        if obj.data is None or not hasattr(obj.data, "materials"):
            continue
        if params.get("replace", True):
            obj.data.materials.clear()
        obj.data.materials.append(mat)
        assigned.append(obj.name)
    return {"material": mat.name, "preset": preset, "assigned": assigned}


def _bsdf(mat):
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        raise ValueError(f"{mat.name} has no Principled BSDF")
    return bsdf


@command("set_pbr_textures")
def set_pbr_textures(params: dict[str, Any]):
    """Wire image maps: base_color, roughness, metallic, normal, displacement, alpha, emission,
    ao."""
    import bpy

    mat = _material(params["material"], create=True)
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    maps = params.get("maps") or {}
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    scale = float(params.get("scale") or 1.0)
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    wired = []
    y = 400
    for kind, path in sorted(maps.items(), key=lambda kv: kv[0] == "ao"):  # AO last
        img = bpy.data.images.load(path, check_existing=True)
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-700, y)
        y -= 300
        nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        if kind not in {"base_color", "emission"}:
            img.colorspace_settings.is_data = True
        if kind == "base_color":
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        elif kind in {"roughness", "metallic"}:
            nt.links.new(tex.outputs["Color"], bsdf.inputs[kind.title()])
        elif kind == "alpha":
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Alpha"])
        elif kind == "emission":
            nt.links.new(
                tex.outputs["Color"],
                _socket(
                    bsdf.inputs, "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
                ),
            )
            _set(bsdf, "Emission Strength", float(params.get("emission_strength") or 1.0))
        elif kind == "normal":
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.inputs["Strength"].default_value = float(params.get("normal_strength") or 1.0)
            nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        elif kind == "displacement":
            disp = nt.nodes.new("ShaderNodeDisplacement")
            disp.inputs["Scale"].default_value = float(params.get("displacement_scale") or 0.05)
            nt.links.new(tex.outputs["Color"], disp.inputs["Height"])
            nt.links.new(disp.outputs["Displacement"], out.inputs["Displacement"])
            if hasattr(mat, "displacement_method"):
                mat.displacement_method = "BOTH"
            elif hasattr(mat.cycles, "displacement_method"):
                mat.cycles.displacement_method = "BOTH"
        elif kind == "ao":
            # AO multiplies the base colour (a bake-friendly approximation).
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            base_link = bsdf.inputs["Base Color"].links
            if base_link:
                nt.links.new(base_link[0].from_socket, mix.inputs[6])
            else:
                mix.inputs[6].default_value = bsdf.inputs["Base Color"].default_value
            nt.links.new(tex.outputs["Color"], mix.inputs[7])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
            raise ValueError(f"Unknown map {kind!r}")
        wired.append(kind)
    return {"material": mat.name, "maps": wired}


@command("set_material_surface")
def set_material_surface(params: dict[str, Any]):
    """Transparency/emission/metal/roughness/normal-strength controls in one call."""
    mat = _material(params["material"])
    bsdf = _bsdf(mat)
    changed = []
    for key in ("metallic", "roughness", "ior", "alpha"):
        if params.get(key) is not None:
            _set(bsdf, {"ior": "IOR"}.get(key, key.title()), float(params[key]))
            changed.append(key)
    if params.get("base_color"):
        bsdf.inputs["Base Color"].default_value = (*params["base_color"][:3], 1)
        changed.append("base_color")
    if params.get("transmission") is not None:
        _set(bsdf, "Transmission", float(params["transmission"]))
        changed.append("transmission")
    if params.get("emission_color") or params.get("emission_strength") is not None:
        if params.get("emission_color"):
            _set(bsdf, "Emission Color", (*params["emission_color"][:3], 1))
        _set(bsdf, "Emission Strength", float(params.get("emission_strength") or 1.0))
        changed.append("emission")
    if params.get("alpha") is not None and float(params["alpha"]) < 1:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
        elif hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"
    if params.get("procedural_bump") is not None:
        nt = mat.node_tree
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = float(params.get("bump_scale") or 30)
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = float(params["procedural_bump"])
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        changed.append("procedural_bump")
    return {"material": mat.name, "changed": changed}
