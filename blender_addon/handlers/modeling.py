"""Extra modeling / CAD-style handlers: booleans, loop cuts, bisect/knife, bridge, dissolve,
raw geometry, spin, precise dimensions, units, measurement and geometry-node scattering."""

from __future__ import annotations

import math
from typing import Any

from ..utils.context import object_mode, require_mesh
from ..utils.objects import get_object, link_object
from . import command


def _bm(obj):
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


def _commit(obj, bm):
    bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {"name": obj.name, "vertices": len(obj.data.vertices), "faces": len(obj.data.polygons)}


@command("boolean_operation")
def boolean_operation(params: dict[str, Any]):
    import bpy

    target = get_object(params["target"])
    cutter = get_object(params["cutter"])
    require_mesh(target)
    op = (params.get("operation") or "DIFFERENCE").upper()
    mod = target.modifiers.new(f"Bool_{cutter.name}", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = (params.get("solver") or "EXACT").upper()
    result: dict[str, Any] = {"target": target.name, "operation": op, "modifier": mod.name}
    if params.get("apply", False):
        with object_mode(target) as override, bpy.context.temp_override(**override):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        result["applied"] = True
    if params.get("hide_cutter", True):
        cutter.display_type = "WIRE"
        cutter.hide_render = True
        if params.get("apply", False):
            cutter.hide_viewport = True
    result["faces"] = len(target.data.polygons)
    return result


@command("loop_cut")
def loop_cut(params: dict[str, Any]):
    """Evenly spaced edge loops across an axis (bisect-based, works on any topology)."""
    import bmesh
    import mathutils

    obj = get_object(params["name"])
    require_mesh(obj)
    axis = "XYZ".index((params.get("axis") or "Z").upper())
    cuts = max(1, min(int(params.get("cuts") or 1), 64))
    bm = _bm(obj)
    lo = min(v.co[axis] for v in bm.verts)
    hi = max(v.co[axis] for v in bm.verts)
    normal = mathutils.Vector((0, 0, 0))
    normal[axis] = 1
    for i in range(1, cuts + 1):
        co = mathutils.Vector((0, 0, 0))
        co[axis] = lo + (hi - lo) * i / (cuts + 1)
        bmesh.ops.bisect_plane(
            bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=normal
        )
    out = _commit(obj, bm)
    out["cuts"] = cuts
    return out


@command("bisect_mesh")
def bisect_mesh(params: dict[str, Any]):
    """Knife/bisect along a world-space plane; optionally clear one side and fill the cut."""
    import bmesh
    import mathutils

    obj = get_object(params["name"])
    require_mesh(obj)
    inv = obj.matrix_world.inverted()
    co = inv @ mathutils.Vector(params.get("plane_co") or (0, 0, 0))
    no = (
        inv.to_3x3().transposed().inverted() @ mathutils.Vector(params.get("plane_no") or (0, 0, 1))
    ).normalized()
    bm = _bm(obj)
    res = bmesh.ops.bisect_plane(
        bm,
        geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
        plane_co=co,
        plane_no=no,
        clear_inner=bool(params.get("clear_inner")),
        clear_outer=bool(params.get("clear_outer")),
    )
    if params.get("fill"):
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges)
    return _commit(obj, bm)


@command("bridge_edge_loops")
def bridge_edge_loops(params: dict[str, Any]):
    """Bridge open boundary loops (e.g. two tube ends after join_objects)."""
    import bmesh

    obj = get_object(params["name"])
    require_mesh(obj)
    bm = _bm(obj)
    edges = [e for e in bm.edges if e.is_boundary]
    if not edges:
        bm.free()
        raise ValueError("Mesh has no open boundary loops to bridge")
    bmesh.ops.bridge_loops(
        bm,
        edges=edges,
        use_pairs=bool(params.get("use_pairs", False)),
        twist_offset=int(params.get("twist") or 0),
    )
    if params.get("segments", 1) > 1:
        new_edges = [e for e in bm.edges if not e.is_boundary and e.select]
        if new_edges:
            bmesh.ops.subdivide_edges(
                bm, edges=new_edges, cuts=int(params["segments"]) - 1, use_grid_fill=True
            )
    return _commit(obj, bm)


@command("dissolve_geometry")
def dissolve_geometry(params: dict[str, Any]):
    """mode=limited (planar cleanup by angle), degenerate, or vertices/edges/faces by index."""
    import bmesh

    obj = get_object(params["name"])
    require_mesh(obj)
    mode = (params.get("mode") or "limited").lower()
    bm = _bm(obj)
    before = len(bm.faces)
    if mode == "limited":
        bmesh.ops.dissolve_limit(
            bm,
            angle_limit=math.radians(float(params.get("angle") or 5.0)),
            verts=bm.verts[:],
            edges=bm.edges[:],
        )
    elif mode == "degenerate":
        bmesh.ops.dissolve_degenerate(
            bm, dist=float(params.get("distance") or 1e-4), edges=bm.edges[:]
        )
    else:
        idx = set(params.get("indices") or [])
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        if mode == "vertices":
            bmesh.ops.dissolve_verts(bm, verts=[bm.verts[i] for i in idx])
        elif mode == "edges":
            bmesh.ops.dissolve_edges(bm, edges=[bm.edges[i] for i in idx])
        elif mode == "faces":
            bmesh.ops.dissolve_faces(bm, faces=[bm.faces[i] for i in idx])
        else:
            bm.free()
            raise ValueError("mode must be limited, degenerate, vertices, edges or faces")
    out = _commit(obj, bm)
    out["faces_before"] = before
    return out


@command("add_mesh_elements")
def add_mesh_elements(params: dict[str, Any]):
    """Append vertices (local coords) plus edges/faces indexing into the NEW vertex list."""
    obj = get_object(params["name"])
    require_mesh(obj)
    bm = _bm(obj)
    new = [bm.verts.new(co) for co in params.get("vertices") or []]
    for a, b in params.get("edges") or []:
        bm.edges.new((new[a], new[b]))
    for face in params.get("faces") or []:
        bm.faces.new([new[i] for i in face])
    if params.get("connect_existing"):
        import bmesh

        bmesh.ops.remove_doubles(
            bm, verts=bm.verts[:], dist=float(params.get("merge_distance") or 1e-4)
        )
    out = _commit(obj, bm)
    out["added_vertices"] = len(new)
    return out


@command("spin_mesh")
def spin_mesh(params: dict[str, Any]):
    """Lathe/revolve the whole mesh profile around an axis (vases, bottles, columns)."""
    import bmesh
    import mathutils

    obj = get_object(params["name"])
    require_mesh(obj)
    bm = _bm(obj)
    axis = mathutils.Vector(
        {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[(params.get("axis") or "Z").upper()]
    )
    bmesh.ops.spin(
        bm,
        geom=bm.verts[:] + bm.edges[:],
        cent=params.get("center") or (0, 0, 0),
        axis=axis,
        angle=math.radians(float(params.get("angle") or 360)),
        steps=int(params.get("steps") or 32),
        use_duplicate=False,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    return _commit(obj, bm)


@command("set_object_dimensions")
def set_object_dimensions(params: dict[str, Any]):
    """Exact size in scene units; ``keep_proportions`` scales uniformly from one axis."""
    import bpy

    obj = get_object(params["name"])
    dims = list(obj.dimensions)
    target = params.get("dimensions") or [None, None, None]
    if params.get("keep_proportions"):
        axis = next(i for i, v in enumerate(target) if v is not None)
        factor = float(target[axis]) / dims[axis] if dims[axis] else 1.0
        obj.scale = [s * factor for s in obj.scale]
    else:
        obj.dimensions = [
            float(t) if t is not None else d for t, d in zip(target, dims, strict=True)
        ]
    if params.get("apply_scale"):
        with object_mode(obj) as override, bpy.context.temp_override(**override):
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.update()
    return {"name": obj.name, "dimensions": list(obj.dimensions), "scale": list(obj.scale)}


@command("set_scene_units")
def set_scene_units(params: dict[str, Any]):
    import bpy

    us = bpy.context.scene.unit_settings
    us.system = (params.get("system") or "METRIC").upper()
    if params.get("length_unit"):
        us.length_unit = params["length_unit"].upper()
    if params.get("scale_length") is not None:
        us.scale_length = float(params["scale_length"])
    if params.get("mass_unit"):
        us.mass_unit = params["mass_unit"].upper()
    return {"system": us.system, "length_unit": us.length_unit, "scale_length": us.scale_length}


@command("measure")
def measure(params: dict[str, Any]):
    """Distance between two objects/points, plus each object's bounds, volume and area."""
    import bmesh
    import bpy
    import mathutils

    def point(v):
        if isinstance(v, str):
            return get_object(v).matrix_world.translation.copy()
        return mathutils.Vector(v)

    out: dict[str, Any] = {}
    if params.get("a") is not None and params.get("b") is not None:
        a, b = point(params["a"]), point(params["b"])
        out["distance"] = (a - b).length
        out["delta"] = list(b - a)
    for name in params.get("objects") or []:
        obj = get_object(name)
        entry = {"dimensions": list(obj.dimensions)}
        if obj.type == "MESH":
            bm = bmesh.new()
            bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
            bm.transform(obj.matrix_world)
            entry["volume"] = abs(bm.calc_volume(signed=True))
            entry["surface_area"] = sum(f.calc_area() for f in bm.faces)
            bm.free()
        out.setdefault("objects", {})[name] = entry
    us = bpy.context.scene.unit_settings
    out["units"] = {
        "system": us.system,
        "length_unit": us.length_unit,
        "scale_length": us.scale_length,
    }
    return out


@command("array_along_curve")
def array_along_curve(params: dict[str, Any]):
    obj = get_object(params["name"])
    curve = get_object(params["curve"])
    arr = obj.modifiers.new("CurveArray", "ARRAY")
    arr.fit_type = "FIT_CURVE"
    arr.curve = curve
    arr.relative_offset_displace = params.get("offset") or (1, 0, 0)
    deform = obj.modifiers.new("CurveDeform", "CURVE")
    deform.object = curve
    deform.deform_axis = (params.get("axis") or "POS_X").upper()
    return {"name": obj.name, "curve": curve.name, "modifiers": [arr.name, deform.name]}


@command("create_gn_scatter")
def create_gn_scatter(params: dict[str, Any]):
    """Non-destructive Geometry Nodes scatter: distribute points on the surface and
    instance a collection with random rotation/scale (keeps the original surface)."""
    import bpy

    surface = get_object(params["surface"])
    coll = bpy.data.collections.get(params["instance_collection"])
    if coll is None:
        raise ValueError("instance_collection not found")
    tree = bpy.data.node_groups.new(
        params.get("name") or f"Scatter_{coll.name}", "GeometryNodeTree"
    )
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    dens = tree.interface.new_socket("Density", in_out="INPUT", socket_type="NodeSocketFloat")
    dens.default_value = float(params.get("density") or 1.0)
    tree.interface.new_socket("Seed", in_out="INPUT", socket_type="NodeSocketInt")
    n = tree.nodes
    gin, gout = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    dist = n.new("GeometryNodeDistributePointsOnFaces")
    info = n.new("GeometryNodeCollectionInfo")
    info.inputs["Separate Children"].default_value = True
    info.inputs["Reset Children"].default_value = True
    info.inputs["Collection"].default_value = coll
    inst = n.new("GeometryNodeInstanceOnPoints")
    inst.inputs["Pick Instance"].default_value = True
    rnd_scale = n.new("FunctionNodeRandomValue")
    rnd_scale.data_type = "FLOAT"
    smin, smax = params.get("scale_range") or (0.8, 1.2)
    _named(rnd_scale.inputs, "Min", "VALUE").default_value = smin
    _named(rnd_scale.inputs, "Max", "VALUE").default_value = smax
    rnd_rot = n.new("FunctionNodeRandomValue")
    rnd_rot.data_type = "FLOAT_VECTOR"
    _named(rnd_rot.inputs, "Max", "VECTOR").default_value = (0, 0, math.tau)
    join = n.new("GeometryNodeJoinGeometry")
    links = tree.links
    links.new(gin.outputs["Geometry"], dist.inputs["Mesh"])
    links.new(gin.outputs["Density"], dist.inputs["Density"])
    links.new(gin.outputs["Seed"], dist.inputs["Seed"])
    links.new(dist.outputs["Points"], inst.inputs["Points"])
    links.new(info.outputs[0], inst.inputs["Instance"])
    links.new(_named(rnd_scale.outputs, "Value", "VALUE"), inst.inputs["Scale"])
    if params.get("align_to_normal") and "Rotation" in dist.outputs:
        # Distribute's Rotation output already aligns +Z to the surface normal.
        links.new(dist.outputs["Rotation"], inst.inputs["Rotation"])
    else:
        links.new(_named(rnd_rot.outputs, "Value", "VECTOR"), inst.inputs["Rotation"])
    links.new(gin.outputs["Geometry"], join.inputs[0])
    links.new(inst.outputs["Instances"], join.inputs[0])
    links.new(join.outputs[0], gout.inputs["Geometry"])
    for i, node in enumerate((gin, dist, info, rnd_scale, rnd_rot, inst, join, gout)):
        node.location = (i * 220 - 800, 0)
    mod = surface.modifiers.new(tree.name, "NODES")
    mod.node_group = tree
    coll.hide_render = False
    if params.get("hide_source_collection", True):
        layer_coll = _find_layer_collection(bpy.context.view_layer.layer_collection, coll.name)
        if layer_coll:
            layer_coll.exclude = True
    return {"surface": surface.name, "node_group": tree.name, "modifier": mod.name}


def _named(sockets, name, stype):
    """Socket by name + type; Random Value repeats names per data type across versions."""
    for s in sockets:
        if s.name == name and s.type == stype and getattr(s, "enabled", True):
            return s
    for s in sockets:
        if s.name == name and s.type == stype:
            return s
    raise ValueError(f"No {stype} socket {name!r}")


def _find_layer_collection(root, name):
    if root.collection.name == name:
        return root
    for child in root.children:
        found = _find_layer_collection(child, name)
        if found:
            return found
    return None


@command("remove_geometry_node")
def remove_geometry_node(params: dict[str, Any]):
    import bpy

    tree = bpy.data.node_groups.get(params["node_group"])
    if tree is None:
        raise ValueError("node_group not found")
    node = tree.nodes.get(params["node"])
    if node is None:
        raise ValueError(f"Node not found; have {[x.name for x in tree.nodes]}")
    tree.nodes.remove(node)
    return {"node_group": tree.name, "removed": params["node"]}


@command("create_parametric_object")
def create_parametric_object(params: dict[str, Any]):
    """Geometry-nodes parametric primitives exposed as modifier inputs:
    gear, pipe, grid_panel, spiral_stairs-like helix, screw-thread rod."""
    import bpy

    kind = (params.get("kind") or "gear").lower()
    mesh = bpy.data.meshes.new(params.get("name") or kind.title())
    obj = bpy.data.objects.new(mesh.name, mesh)
    link_object(obj, params.get("collection"))
    obj.location = params.get("location") or (0, 0, 0)
    tree = bpy.data.node_groups.new(f"Param_{kind}", "GeometryNodeTree")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n, links = tree.nodes, tree.links
    out = n.new("NodeGroupOutput")

    def sock(name, stype, default):
        s = tree.interface.new_socket(name, in_out="INPUT", socket_type=stype)
        s.default_value = default
        return name

    gin = n.new("NodeGroupInput")
    if kind == "gear":
        teeth = int(params.get("teeth") or 16)
        sock("Teeth", "NodeSocketInt", teeth)
        sock("Radius", "NodeSocketFloat", float(params.get("radius") or 1.0))
        sock("Thickness", "NodeSocketFloat", float(params.get("thickness") or 0.3))
        star = n.new("GeometryNodeCurveStar")
        links.new(gin.outputs["Teeth"], star.inputs["Points"])
        links.new(gin.outputs["Radius"], star.inputs["Outer Radius"])
        mul = n.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = 0.8
        links.new(gin.outputs["Radius"], mul.inputs[0])
        links.new(mul.outputs[0], star.inputs["Inner Radius"])
        fill = n.new("GeometryNodeFillCurve")
        links.new(star.outputs["Curve"], fill.inputs["Curve"])
        ext = n.new("GeometryNodeExtrudeMesh")
        links.new(fill.outputs["Mesh"], ext.inputs["Mesh"])
        links.new(gin.outputs["Thickness"], ext.inputs["Offset Scale"])
        links.new(ext.outputs["Mesh"], out.inputs[0])
    elif kind in {"pipe", "helix"}:
        sock("Radius", "NodeSocketFloat", float(params.get("radius") or 0.1))
        sock("Length", "NodeSocketFloat", float(params.get("length") or 2.0))
        if kind == "helix":
            sock("Turns", "NodeSocketFloat", float(params.get("turns") or 5))
            curve = n.new("GeometryNodeCurveSpiral")
            links.new(gin.outputs["Turns"], curve.inputs["Rotations"])
            links.new(gin.outputs["Length"], curve.inputs["Height"])
        else:
            curve = n.new("GeometryNodeCurvePrimitiveLine")
            comb = n.new("ShaderNodeCombineXYZ")
            links.new(gin.outputs["Length"], comb.inputs["Z"])
            links.new(comb.outputs[0], curve.inputs["End"])
        prof = n.new("GeometryNodeCurvePrimitiveCircle")
        links.new(gin.outputs["Radius"], prof.inputs["Radius"])
        c2m = n.new("GeometryNodeCurveToMesh")
        links.new(curve.outputs["Curve"], c2m.inputs["Curve"])
        links.new(prof.outputs["Curve"], c2m.inputs["Profile Curve"])
        if "Fill Caps" in c2m.inputs:
            c2m.inputs["Fill Caps"].default_value = True
        links.new(c2m.outputs["Mesh"], out.inputs[0])
    elif kind == "grid_panel":
        sock("Size X", "NodeSocketFloat", float(params.get("size_x") or 2.0))
        sock("Size Y", "NodeSocketFloat", float(params.get("size_y") or 2.0))
        sock("Holes", "NodeSocketInt", int(params.get("holes") or 6))
        grid = n.new("GeometryNodeMeshGrid")
        links.new(gin.outputs["Size X"], grid.inputs["Size X"])
        links.new(gin.outputs["Size Y"], grid.inputs["Size Y"])
        links.new(gin.outputs["Holes"], grid.inputs["Vertices X"])
        links.new(gin.outputs["Holes"], grid.inputs["Vertices Y"])
        ins = n.new("GeometryNodeExtrudeMesh")
        ins.inputs["Offset Scale"].default_value = 0.05
        links.new(grid.outputs["Mesh"], ins.inputs["Mesh"])
        links.new(ins.outputs["Mesh"], out.inputs[0])
    else:
        bpy.data.node_groups.remove(tree)
        raise ValueError("kind must be gear, pipe, helix or grid_panel")
    mod = obj.modifiers.new(tree.name, "NODES")
    mod.node_group = tree
    inputs = [s.name for s in tree.interface.items_tree if getattr(s, "in_out", "") == "INPUT"]
    return {
        "name": obj.name,
        "node_group": tree.name,
        "parameters": inputs,
        "hint": "Change parameters with set_geometry_node_input or modify_modifier",
    }
