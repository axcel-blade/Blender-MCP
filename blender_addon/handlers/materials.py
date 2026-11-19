"""Material handlers."""

from __future__ import annotations

from typing import Any

from . import command


def _principled(mat):
    if not mat.use_nodes:
        mat.use_nodes = True
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _set_input(node, name: str, value) -> None:
    socket = node.inputs.get(name)
    if socket is None:
        raise ValueError(f"Unknown input: {name}")
    socket.default_value = value


def _create_mat(
    name=None,
    base_color=None,
    metallic=0.0,
    roughness=0.5,
    emission_strength=None,
    transmission=None,
    alpha=None,
    ior=None,
):
    import bpy

    mat = bpy.data.materials.new(name=name or "Material")
    mat.use_nodes = True
    node = _principled(mat)
    if base_color is not None:
        color = list(base_color) + [1.0] if len(base_color) == 3 else list(base_color)
        _set_input(node, "Base Color", color)
    _set_input(node, "Metallic", float(metallic))
    _set_input(node, "Roughness", float(roughness))
    if emission_strength is not None and "Emission Strength" in node.inputs:
        _set_input(node, "Emission Strength", float(emission_strength))
        if base_color is not None and "Emission Color" in node.inputs:
            color = list(base_color) + [1.0] if len(base_color) == 3 else list(base_color)
            _set_input(node, "Emission Color", color)
    if transmission is not None:
        key = "Transmission Weight" if "Transmission Weight" in node.inputs else "Transmission"
        if key in node.inputs:
            _set_input(node, key, float(transmission))
    if alpha is not None and "Alpha" in node.inputs:
        _set_input(node, "Alpha", float(alpha))
        mat.blend_method = "BLEND"
    if ior is not None and "IOR" in node.inputs:
        _set_input(node, "IOR", float(ior))
    return {"name": mat.name, "use_nodes": True}


@command("create_material")
@command("create_basic_shader")
def create_material(params: dict[str, Any]):
    return _create_mat(
        params.get("name"),
        params.get("base_color") or params.get("color"),
        params.get("metallic", 0.0),
        params.get("roughness", 0.5),
    )


@command("create_emission_material")
def create_emission_material(params: dict[str, Any]):
    return _create_mat(
        params.get("name"),
        params.get("color") or [1, 1, 1],
        emission_strength=params.get("strength", 5.0),
    )


@command("create_metallic_material")
def create_metallic_material(params: dict[str, Any]):
    return _create_mat(
        params.get("name"),
        params.get("color") or [0.8, 0.8, 0.8],
        metallic=1.0,
        roughness=params.get("roughness", 0.2),
    )


@command("create_glass_material")
def create_glass_material(params: dict[str, Any]):
    return _create_mat(
        params.get("name"),
        [1, 1, 1, 1],
        roughness=params.get("roughness", 0.0),
        transmission=1.0,
        ior=params.get("ior", 1.45),
    )


@command("create_transparent_material")
def create_transparent_material(params: dict[str, Any]):
    return _create_mat(
        params.get("name"),
        params.get("color") or [1, 1, 1],
        alpha=params.get("alpha", 0.3),
        roughness=0.1,
    )


@command("assign_material")
def assign_material(params: dict[str, Any]):
    import bpy

    from ..utils.objects import get_object

    obj = get_object(params["object_name"])
    mat = bpy.data.materials.get(params["material_name"])
    if mat is None:
        raise ValueError(f"Material not found: {params['material_name']}")
    slot = int(params.get("slot") or 0)
    if not obj.data.materials:
        obj.data.materials.append(mat)
    elif slot < len(obj.data.materials):
        obj.data.materials[slot] = mat
    else:
        obj.data.materials.append(mat)
    return {"object": obj.name, "material": mat.name, "slot": slot}


@command("remove_material")
def remove_material(params: dict[str, Any]):
    from ..utils.objects import get_object

    obj = get_object(params["object_name"])
    slot = int(params.get("slot") or 0)
    if slot < len(obj.material_slots):
        obj.data.materials.pop(index=slot)
    return {"object": obj.name, "removed_slot": slot}


@command("modify_material")
@command("set_material_properties")
def modify_material(params: dict[str, Any]):
    import bpy

    mat = bpy.data.materials.get(params["name"])
    if mat is None:
        raise ValueError(f"Material not found: {params['name']}")
    node = _principled(mat)
    settings = params.get("settings") or params.get("properties") or {}
    mapping = {
        "base_color": "Base Color",
        "color": "Base Color",
        "metallic": "Metallic",
        "roughness": "Roughness",
        "ior": "IOR",
        "alpha": "Alpha",
        "emission_strength": "Emission Strength",
        "transmission": "Transmission Weight",
    }
    for key, value in settings.items():
        input_name = mapping.get(key, key)
        if input_name == "Base Color" and isinstance(value, (list, tuple)) and len(value) == 3:
            value = list(value) + [1.0]
        if input_name == "Transmission Weight" and input_name not in node.inputs:
            input_name = "Transmission"
        _set_input(node, input_name, value)
    return {"name": mat.name, "updated": list(settings.keys())}


@command("set_material_color")
def set_material_color(params: dict[str, Any]):
    return modify_material({"name": params["name"], "settings": {"base_color": params["color"]}})


@command("get_material_info")
@command("get_material_nodes")
def get_material_info(params: dict[str, Any]):
    import bpy

    mat = bpy.data.materials.get(params["name"])
    if mat is None:
        raise ValueError(f"Material not found: {params['name']}")
    nodes = []
    if mat.use_nodes:
        for n in mat.node_tree.nodes:
            nodes.append({"name": n.name, "type": n.type, "label": n.label})
    return {"name": mat.name, "use_nodes": mat.use_nodes, "nodes": nodes}


@command("list_materials")
def list_materials(params: dict[str, Any]):
    import bpy

    return [{"name": m.name, "users": m.users, "use_nodes": m.use_nodes} for m in bpy.data.materials]


@command("set_material_nodes")
def set_material_nodes(params: dict[str, Any]):
    import bpy

    mat = bpy.data.materials.get(params["name"])
    if mat is None:
        raise ValueError(f"Material not found: {params['name']}")
    mat.use_nodes = True
    nt = mat.node_tree
    results = []
    for op in params.get("operations") or []:
        kind = op.get("op")
        if kind == "add_node":
            node = nt.nodes.new(op["type"])
            if op.get("name"):
                node.name = op["name"]
            results.append({"added": node.name, "type": node.type})
        elif kind == "link":
            fn = nt.nodes[op["from_node"]]
            tn = nt.nodes[op["to_node"]]
            nt.links.new(fn.outputs[op["from_socket"]], tn.inputs[op["to_socket"]])
            results.append({"linked": True})
        elif kind == "set_default":
            node = nt.nodes[op["node"]]
            node.inputs[op["input"]].default_value = op["value"]
            results.append({"set": op["input"]})
        else:
            raise ValueError(f"Unknown node op: {kind}")
    return {"name": mat.name, "results": results}


@command("assign_texture")
def assign_texture(params: dict[str, Any]):
    import bpy
    from pathlib import Path

    mat = bpy.data.materials.get(params["material_name"])
    if mat is None:
        raise ValueError(f"Material not found: {params['material_name']}")
    path = Path(params["image_path"]).expanduser()
    if not path.exists():
        raise ValueError(f"Image not found: {path}")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = _principled(mat)
    img = bpy.data.images.load(str(path))
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    input_name = params.get("input_name") or "Base Color"
    nt.links.new(tex.outputs["Color"], bsdf.inputs[input_name])
    return {"material": mat.name, "image": img.name, "input": input_name}
