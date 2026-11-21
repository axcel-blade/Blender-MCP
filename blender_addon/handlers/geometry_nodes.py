"""Geometry Nodes handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import get_object
from . import command


@command("create_geometry_nodes_modifier")
def create_geometry_nodes_modifier(params: dict[str, Any]):
    import bpy

    obj = get_object(params["name"])
    mod = obj.modifiers.new("GeometryNodes", "NODES")
    group_name = params.get("group_name")
    if group_name and group_name in bpy.data.node_groups:
        mod.node_group = bpy.data.node_groups[group_name]
    elif group_name:
        group = bpy.data.node_groups.new(group_name, "GeometryNodeTree")
        mod.node_group = group
    return {
        "object": obj.name,
        "modifier": mod.name,
        "group": getattr(mod.node_group, "name", None),
    }


@command("create_node_group")
def create_node_group(params: dict[str, Any]):
    import bpy

    name = params.get("name") or "GeometryNodes"
    group = bpy.data.node_groups.new(name, "GeometryNodeTree")
    # Blender 4+ interface API differs; create minimal group
    try:
        group.interface.new_socket(
            name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
        )
        group.interface.new_socket(
            name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
        )
    except Exception:
        pass
    return {"name": group.name, "type": group.bl_idname}


@command("add_geometry_node")
def add_geometry_node(params: dict[str, Any]):
    import bpy

    group = bpy.data.node_groups.get(params["group_name"])
    if group is None:
        raise ValueError(f"Node group not found: {params['group_name']}")
    node = group.nodes.new(params["node_type"])
    if params.get("node_name"):
        node.name = params["node_name"]
    return {"group": group.name, "node": node.name, "type": node.bl_idname}


@command("connect_geometry_nodes")
def connect_geometry_nodes(params: dict[str, Any]):
    import bpy

    group = bpy.data.node_groups.get(params["group_name"])
    if group is None:
        raise ValueError(f"Node group not found: {params['group_name']}")
    fn = group.nodes[params["from_node"]]
    tn = group.nodes[params["to_node"]]
    out_sock = fn.outputs.get(params["from_socket"]) or fn.outputs[params["from_socket"]]
    in_sock = tn.inputs.get(params["to_socket"]) or tn.inputs[params["to_socket"]]
    group.links.new(out_sock, in_sock)
    return {"linked": True}


@command("set_geometry_node_input")
def set_geometry_node_input(params: dict[str, Any]):
    import bpy

    group = bpy.data.node_groups.get(params["group_name"])
    if group is None:
        raise ValueError(f"Node group not found: {params['group_name']}")
    node = group.nodes[params["node_name"]]
    sock = node.inputs.get(params["input_name"])
    if sock is None:
        raise ValueError(f"Input not found: {params['input_name']}")
    sock.default_value = params["value"]
    return {"node": node.name, "input": params["input_name"]}


@command("inspect_node_group")
def inspect_node_group(params: dict[str, Any]):
    import bpy

    group = bpy.data.node_groups.get(params["group_name"])
    if group is None:
        raise ValueError(f"Node group not found: {params['group_name']}")
    return {
        "name": group.name,
        "nodes": [{"name": n.name, "type": n.bl_idname, "label": n.label} for n in group.nodes],
        "links": [
            {
                "from": link.from_node.name,
                "from_socket": link.from_socket.name,
                "to": link.to_node.name,
                "to_socket": link.to_socket.name,
            }
            for link in group.links
        ],
    }


@command("list_geometry_node_types")
def list_geometry_node_types(params: dict[str, Any]):
    # Representative set — AI should inspect sockets via get_node_socket_info after adding.
    return {
        "types": [
            "NodeGroupInput",
            "NodeGroupOutput",
            "GeometryNodeMeshCube",
            "GeometryNodeMeshCircle",
            "GeometryNodeMeshGrid",
            "GeometryNodeMeshUVSphere",
            "GeometryNodeMeshCylinder",
            "GeometryNodeMeshCone",
            "GeometryNodeTransformGeometry",
            "GeometryNodeJoinGeometry",
            "GeometryNodeRealizeInstances",
            "GeometryNodeInstanceOnPoints",
            "GeometryNodeDistributePointsOnFaces",
            "ShaderNodeMath",
            "FunctionNodeCompare",
            "GeometryNodeSetPosition",
            "GeometryNodeSetMaterial",
        ]
    }


@command("get_node_socket_info")
def get_node_socket_info(params: dict[str, Any]):
    import bpy

    group = bpy.data.node_groups.get(params["group_name"])
    if group is None:
        raise ValueError(f"Node group not found: {params['group_name']}")
    node = group.nodes[params["node_name"]]
    return {
        "node": node.name,
        "type": node.bl_idname,
        "inputs": [{"name": s.name, "type": s.type, "enabled": s.enabled} for s in node.inputs],
        "outputs": [{"name": s.name, "type": s.type, "enabled": s.enabled} for s in node.outputs],
    }
