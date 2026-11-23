"""Compositor handlers (pre-5.0 scene.node_tree and 5.0+ compositing_node_group)."""

from __future__ import annotations

from typing import Any

from ..utils.context import compositor_tree
from . import command


def _ensure_base(tree):
    """Make sure the tree has Render Layers -> output; return (render_layers, output)."""
    nodes = tree.nodes
    rl = next((n for n in nodes if n.type == "R_LAYERS"), None) or nodes.new(
        "CompositorNodeRLayers"
    )
    rl.location = (-400, 0)
    out = next((n for n in nodes if n.type in {"COMPOSITE", "GROUP_OUTPUT"}), None)
    if out is None:
        if hasattr(tree, "interface"):  # 5.0 compositor node group
            if not any(
                s.in_out == "OUTPUT" for s in tree.interface.items_tree if s.item_type == "SOCKET"
            ):
                tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            out = nodes.new("NodeGroupOutput")
        else:
            out = nodes.new("CompositorNodeComposite")
        out.location = (600, 0)
    if not out.inputs[0].is_linked:
        tree.links.new(rl.outputs["Image"], out.inputs[0])
    return rl, out


def _node(tree, name: str):
    node = tree.nodes.get(name)
    if node is None:
        raise ValueError(f"Compositor node not found: {name}; have {[n.name for n in tree.nodes]}")
    return node


def _socket(sockets, key):
    if isinstance(key, int):
        return sockets[key]
    if key in sockets:
        return sockets[key]
    match = next(
        (s for s in sockets if s.identifier == key or s.name.lower() == str(key).lower()), None
    )
    if match is None:
        raise ValueError(f"Socket {key!r} not found; have {[s.name for s in sockets]}")
    return match


@command("enable_compositor")
def enable_compositor(params: dict[str, Any]):
    tree = compositor_tree(create=True)
    rl, out = _ensure_base(tree)
    return {
        "tree": tree.name,
        "render_layers": rl.name,
        "output": out.name,
        "nodes": [n.name for n in tree.nodes],
    }


@command("add_compositor_node")
def add_compositor_node(params: dict[str, Any]):
    tree = compositor_tree(create=True)
    node = tree.nodes.new(params["node_type"])
    if params.get("name"):
        node.name = node.label = params["name"]
    if params.get("location"):
        node.location = params["location"]
    for key, value in (params.get("inputs") or {}).items():
        _socket(node.inputs, key).default_value = value
    for key, value in (params.get("properties") or {}).items():
        setattr(node, key, value)
    return {
        "name": node.name,
        "type": node.bl_idname,
        "inputs": [s.name for s in node.inputs],
        "outputs": [s.name for s in node.outputs],
    }


@command("connect_compositor_nodes")
def connect_compositor_nodes(params: dict[str, Any]):
    tree = compositor_tree(create=True)
    src = _node(tree, params["from_node"])
    dst = _node(tree, params["to_node"])
    link = tree.links.new(
        _socket(src.outputs, params.get("from_socket", 0)),
        _socket(dst.inputs, params.get("to_socket", 0)),
    )
    return {
        "from": f"{src.name}.{link.from_socket.name}",
        "to": f"{dst.name}.{link.to_socket.name}",
    }


@command("set_compositor_node")
def set_compositor_node(params: dict[str, Any]):
    tree = compositor_tree(create=True)
    node = _node(tree, params["node"])
    for key, value in (params.get("inputs") or {}).items():
        _socket(node.inputs, key).default_value = value
    for key, value in (params.get("properties") or {}).items():
        if not hasattr(node, key):
            raise ValueError(f"{node.bl_idname} has no property {key!r}")
        setattr(node, key, value)
    return {"node": node.name}


@command("remove_compositor_node")
def remove_compositor_node(params: dict[str, Any]):
    tree = compositor_tree(create=False)
    if tree is None:
        raise ValueError("Compositor is not enabled")
    node = _node(tree, params["node"])
    tree.nodes.remove(node)
    return {"removed": params["node"]}


def _insert_before_output(tree, node, in_key=0, out_key=0):
    """Splice ``node`` into the link that feeds the output's image input."""
    _, out = _ensure_base(tree)
    target = out.inputs[0]
    prev = target.links[0].from_socket if target.is_linked else None
    if prev is not None:
        tree.links.new(prev, _socket(node.inputs, in_key))
    tree.links.new(_socket(node.outputs, out_key), target)
    node.location = (out.location.x - 200, out.location.y)
    out.location.x += 220


def _typed(sockets, name, stype):
    """Socket by name and type (Mix nodes have same-named sockets per data type)."""
    match = next((s for s in sockets if s.name == name and s.type == stype and s.enabled), None)
    if match is None:
        match = next((s for s in sockets if s.name == name and s.type == stype), None)
    if match is None:
        raise ValueError(f"No {stype} socket {name!r}")
    return match


_GLARE_MENU = {
    "BLOOM": "Bloom",
    "FOG_GLOW": "Fog Glow",
    "STREAKS": "Streaks",
    "GHOSTS": "Ghosts",
    "SIMPLE_STAR": "Simple Star",
    "SUN_BEAMS": "Sun Beams",
}


def _set_input(node, names, value):
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return True
    return False


@command("apply_compositor_effect")
def apply_compositor_effect(params: dict[str, Any]):
    """Insert a finished effect: glare/bloom, blur, color_grade, vignette, denoise,
    lens_distortion, sharpen, brightness_contrast, exposure. Effects stack in call order."""
    tree = compositor_tree(create=True)
    _ensure_base(tree)
    effect = (params.get("effect") or "glare").lower()
    s = params.get("settings") or {}
    nodes = tree.nodes
    if effect in {"glare", "bloom"}:
        n = nodes.new("CompositorNodeGlare")
        glare = "BLOOM" if effect == "bloom" else s.get("glare_type", "FOG_GLOW")
        try:
            n.glare_type = glare
        except (TypeError, AttributeError):  # 5.x: glare type is a menu input socket
            _set_input(n, ["Type"], _GLARE_MENU.get(glare, glare))
        if hasattr(n, "threshold"):
            n.threshold = float(s.get("threshold", 1.0))
        else:
            _set_input(n, ["Threshold"], float(s.get("threshold", 1.0)))
        _set_input(n, ["Strength"], float(s.get("strength", 1.0)))
        _insert_before_output(tree, n)
    elif effect == "blur":
        n = nodes.new("CompositorNodeBlur")
        size = int(s.get("size", 10))
        if hasattr(n, "size_x"):
            n.size_x = n.size_y = size
        else:
            _set_input(n, ["Size"], (size, size))
        _insert_before_output(tree, n)
    elif effect == "color_grade":
        n = nodes.new("CompositorNodeColorBalance")
        lift, gamma, gain = (
            s.get("lift", (1, 1, 1)),
            s.get("gamma", (1, 1, 1)),
            s.get("gain", (1, 1, 1)),
        )
        if hasattr(n, "lift"):
            n.lift, n.gamma, n.gain = lift[:3], gamma[:3], gain[:3]
        else:
            # 5.x: each wheel is a same-named VALUE + RGBA socket pair; set the colour one.
            _typed(n.inputs, "Lift", "RGBA").default_value = (*lift[:3], 1)
            _typed(n.inputs, "Gamma", "RGBA").default_value = (*gamma[:3], 1)
            _typed(n.inputs, "Gain", "RGBA").default_value = (*gain[:3], 1)
        _insert_before_output(tree, n, in_key="Image")
        if s.get("saturation") is not None:
            hs = nodes.new("CompositorNodeHueSat")
            _set_input(hs, ["Saturation"], float(s["saturation"]))
            _insert_before_output(tree, hs, in_key="Image")
    elif effect == "vignette":
        mask = nodes.new("CompositorNodeEllipseMask")
        if hasattr(mask, "width"):
            mask.width, mask.height = 0.85, 0.85
        else:
            _set_input(mask, ["Size"], (0.85, 0.85))
        blur = nodes.new("CompositorNodeBlur")
        if hasattr(blur, "size_x"):
            blur.size_x = blur.size_y = 200
        else:
            _set_input(blur, ["Size"], (200, 200))
        tree.links.new(mask.outputs[0], _socket(blur.inputs, "Image"))
        import bpy

        legacy_mix = hasattr(bpy.types, "CompositorNodeMixRGB")
        mix = nodes.new("CompositorNodeMixRGB" if legacy_mix else "ShaderNodeMix")
        if mix.bl_idname == "ShaderNodeMix":
            mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
            a, b = _typed(mix.inputs, "A", "RGBA"), _typed(mix.inputs, "B", "RGBA")
            _insert_before_output(
                tree,
                mix,
                in_key=a.identifier,
                out_key=_typed(mix.outputs, "Result", "RGBA").identifier,
            )
            tree.links.new(blur.outputs[0], b)
        else:
            mix.blend_type = "MULTIPLY"
            _insert_before_output(tree, mix, in_key=1)
            tree.links.new(blur.outputs[0], mix.inputs[0])
        mask.location = (mix.location.x - 600, mix.location.y - 300)
        blur.location = (mix.location.x - 350, mix.location.y - 300)
        n = mix
    elif effect == "denoise":
        n = nodes.new("CompositorNodeDenoise")
        _insert_before_output(tree, n, in_key="Image")
    elif effect == "lens_distortion":
        n = nodes.new("CompositorNodeLensdist")
        _set_input(n, ["Distort", "Distortion"], float(s.get("distortion", -0.02)))
        _set_input(n, ["Dispersion"], float(s.get("dispersion", 0.01)))
        _insert_before_output(tree, n)
    elif effect == "sharpen":
        n = nodes.new("CompositorNodeFilter")
        try:
            n.filter_type = "SHARPEN"
        except (TypeError, AttributeError):  # 5.x: menu socket with display names
            _set_input(n, ["Type"], "Box Sharpen")
        _set_input(n, ["Fac", "Factor"], float(s.get("amount", 0.3)))
        _insert_before_output(tree, n, in_key="Image")
    elif effect == "brightness_contrast":
        n = nodes.new("CompositorNodeBrightContrast")
        _set_input(n, ["Bright", "Brightness"], float(s.get("brightness", 0.0)))
        _set_input(n, ["Contrast"], float(s.get("contrast", 10.0)))
        _insert_before_output(tree, n, in_key="Image")
    elif effect == "exposure":
        n = nodes.new("CompositorNodeExposure")
        _set_input(n, ["Exposure"], float(s.get("exposure", 0.5)))
        _insert_before_output(tree, n, in_key="Image")
    else:
        raise ValueError("Unknown effect")
    return {"effect": effect, "node": n.name, "nodes": [x.name for x in tree.nodes]}


@command("composite_over_image")
def composite_over_image(params: dict[str, Any]):
    """Alpha-over the render onto a background image file (film_transparent is enabled)."""
    import bpy

    tree = compositor_tree(create=True)
    rl, out = _ensure_base(tree)
    bpy.context.scene.render.film_transparent = True
    img_node = tree.nodes.new("CompositorNodeImage")
    img_node.image = bpy.data.images.load(params["path"], check_existing=True)
    scale = tree.nodes.new("CompositorNodeScale")
    try:
        scale.space = "RENDER_SIZE"
    except (TypeError, AttributeError):
        _set_input(scale, ["Type"], "RENDER_SIZE")
    tree.links.new(img_node.outputs[0], scale.inputs[0])
    over = tree.nodes.new("CompositorNodeAlphaOver")
    tree.links.new(scale.outputs[0], over.inputs[1])
    tree.links.new(rl.outputs["Image"], over.inputs[2])
    tree.links.new(over.outputs[0], out.inputs[0])
    return {"background": img_node.image.name, "node": over.name}


@command("get_compositor_info")
def get_compositor_info(params: dict[str, Any]):
    tree = compositor_tree(create=False)
    if tree is None:
        return {"enabled": False, "nodes": []}
    return {
        "enabled": True,
        "tree": tree.name,
        "nodes": [
            {"name": n.name, "type": n.bl_idname, "location": list(n.location)} for n in tree.nodes
        ],
        "links": [
            f"{lk.from_node.name}.{lk.from_socket.name} -> {lk.to_node.name}.{lk.to_socket.name}"
            for lk in tree.links
        ],
    }
