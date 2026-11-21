"""Object creation and modification handlers."""

from __future__ import annotations

from typing import Any

from ..utils.objects import active_select, get_object, link_object, serialize_object, set_transform
from . import command

_PRIMITIVE_OPS = {
    "cube": "mesh.primitive_cube_add",
    "uv_sphere": "mesh.primitive_uv_sphere_add",
    "ico_sphere": "mesh.primitive_ico_sphere_add",
    "cylinder": "mesh.primitive_cylinder_add",
    "cone": "mesh.primitive_cone_add",
    "torus": "mesh.primitive_torus_add",
    "plane": "mesh.primitive_plane_add",
    "circle": "mesh.primitive_circle_add",
    "sphere": "mesh.primitive_uv_sphere_add",
}


def _create_primitive(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    primitive = (params.get("primitive") or params.get("object_type") or "cube").lower()
    op_name = _PRIMITIVE_OPS.get(primitive)
    if not op_name:
        raise ValueError(f"Unsupported primitive: {primitive}")

    location = params.get("location") or [0, 0, 0]
    rotation = params.get("rotation") or [0, 0, 0]
    kwargs: dict[str, Any] = {"location": location, "rotation": rotation}

    if primitive in {"cube", "plane"} and params.get("size") is not None:
        kwargs["size"] = params["size"]
    if primitive in {"uv_sphere", "sphere", "ico_sphere", "cylinder", "cone", "circle"}:
        if params.get("radius") is not None:
            kwargs["radius"] = params["radius"]
    if primitive == "ico_sphere" and params.get("subdivisions") is not None:
        kwargs["subdivisions"] = params["subdivisions"]
    if primitive in {"uv_sphere", "sphere"}:
        if params.get("segments") is not None:
            kwargs["segments"] = params["segments"]
        if params.get("rings") is not None:
            kwargs["ring_count"] = params["rings"]
    if primitive in {"cylinder", "cone"} and params.get("depth") is not None:
        kwargs["depth"] = params["depth"]
    if primitive == "cone":
        if params.get("radius1") is not None:
            kwargs["radius1"] = params["radius1"]
        if params.get("radius2") is not None:
            kwargs["radius2"] = params["radius2"]
    if primitive == "torus":
        if params.get("major_radius") is not None:
            kwargs["major_radius"] = params["major_radius"]
        if params.get("minor_radius") is not None:
            kwargs["minor_radius"] = params["minor_radius"]
    if primitive in {"cylinder", "circle"} and params.get("vertices") is not None:
        kwargs["vertices"] = params["vertices"]

    getattr(bpy.ops, op_name.split(".", 1)[0])
    # Resolve operator: bpy.ops.mesh.primitive_cube_add
    module, name = op_name.split(".", 1)
    op = getattr(getattr(bpy.ops, module), name)
    op(**kwargs)

    obj = bpy.context.view_layer.objects.active
    if params.get("name"):
        obj.name = params["name"]
        if obj.data:
            obj.data.name = params["name"]
    if params.get("scale"):
        obj.scale = params["scale"]
    if params.get("collection"):
        link_object(obj, params["collection"])
    if params.get("smooth", True) and obj.type == "MESH":
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return serialize_object(obj)


@command("create_primitive")
@command("create_object")
@command("create_cube")
@command("create_sphere")
@command("create_uv_sphere")
@command("create_ico_sphere")
@command("create_cylinder")
@command("create_cone")
@command("create_torus")
@command("create_plane")
@command("create_circle")
def create_primitive(params: dict[str, Any]) -> dict[str, Any]:
    # Alias commands inject primitive via tool wrappers when needed
    if "primitive" not in params and "object_type" not in params:
        # Infer from calling conventions — tools pass primitive explicitly for create_* wrappers
        pass
    return _create_primitive(params)


@command("create_mesh")
def create_mesh(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    mesh = bpy.data.meshes.new(params.get("name") or "Mesh")
    obj = bpy.data.objects.new(params.get("name") or "Mesh", mesh)
    link_object(obj, params.get("collection"))
    if params.get("location"):
        obj.location = params["location"]
    return serialize_object(obj)


@command("create_text")
def create_text(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    curve = bpy.data.curves.new(params.get("name") or "Text", type="FONT")
    curve.body = params.get("text") or "Text"
    obj = bpy.data.objects.new(params.get("name") or "Text", curve)
    link_object(obj, params.get("collection"))
    if params.get("location"):
        obj.location = params["location"]
    return serialize_object(obj)


@command("create_empty")
def create_empty(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    obj = bpy.data.objects.new(params.get("name") or "Empty", None)
    obj.empty_display_type = params.get("empty_display_type") or "PLAIN_AXES"
    link_object(obj, params.get("collection"))
    if params.get("location"):
        obj.location = params["location"]
    return serialize_object(obj)


@command("create_curve")
def create_curve(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    curve = bpy.data.curves.new(params.get("name") or "Curve", type="CURVE")
    curve.dimensions = "3D"
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(1)
    spline.bezier_points[0].co = (0, 0, 0)
    spline.bezier_points[1].co = (1, 0, 0)
    obj = bpy.data.objects.new(params.get("name") or "Curve", curve)
    link_object(obj, params.get("collection"))
    if params.get("location"):
        obj.location = params["location"]
    return serialize_object(obj)


@command("duplicate_object")
def duplicate_object(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    obj = get_object(params["name"])
    active_select(obj)
    bpy.ops.object.duplicate(linked=bool(params.get("linked", False)))
    new_obj = bpy.context.view_layer.objects.active
    if params.get("new_name"):
        new_obj.name = params["new_name"]
    return serialize_object(new_obj)


@command("create_array_of_objects")
def create_array_of_objects(params: dict[str, Any]) -> dict[str, Any]:
    import mathutils

    obj = get_object(params["name"])
    count = int(params.get("count") or 3)
    offset = params.get("offset") or [2.0, 0.0, 0.0]
    created = []
    for i in range(1, count):
        new_obj = obj.copy()
        if obj.data:
            new_obj.data = obj.data.copy()
        new_obj.location = mathutils.Vector(obj.location) + mathutils.Vector(offset) * i
        link_object(new_obj, obj.users_collection[0].name if obj.users_collection else None)
        created.append(serialize_object(new_obj))
    return {"source": obj.name, "created": created}


@command("modify_object")
def modify_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    set_transform(obj, params.get("location"), params.get("rotation"), params.get("scale"))
    if params.get("dimensions") is not None:
        obj.dimensions = params["dimensions"]
    return serialize_object(obj)


@command("move_object")
def move_object(params: dict[str, Any]) -> dict[str, Any]:
    import mathutils

    obj = get_object(params["name"])
    location = params["location"]
    if (params.get("space") or "world") == "world":
        obj.matrix_world.translation = mathutils.Vector(location)
    else:
        obj.location = location
    return serialize_object(obj)


@command("rotate_object")
def rotate_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    obj.rotation_euler = params["rotation"]
    return serialize_object(obj)


@command("scale_object")
def scale_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    obj.scale = params["scale"]
    return serialize_object(obj)


@command("set_object_transform")
def set_object_transform(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    set_transform(obj, params.get("location"), params.get("rotation"), params.get("scale"))
    return serialize_object(obj)


@command("rename_object")
def rename_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    obj.name = params["new_name"]
    return serialize_object(obj)


@command("set_object_origin")
def set_object_origin(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    obj = get_object(params["name"])
    active_select(obj)
    bpy.ops.object.origin_set(type=params.get("origin_type") or "ORIGIN_GEOMETRY")
    return serialize_object(obj)


@command("set_object_visibility")
def set_object_visibility(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    if params.get("hide_viewport") is not None:
        obj.hide_viewport = params["hide_viewport"]
    if params.get("hide_render") is not None:
        obj.hide_render = params["hide_render"]
    if params.get("hide_select") is not None:
        obj.hide_select = params["hide_select"]
    return serialize_object(obj)


@command("set_object_shading")
def set_object_shading(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    if obj.type != "MESH":
        raise ValueError("Object is not a mesh")
    smooth = bool(params.get("smooth", True))
    for poly in obj.data.polygons:
        poly.use_smooth = smooth
    return serialize_object(obj)


@command("set_object_parent")
def set_object_parent(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    obj = get_object(params["name"])
    parent = get_object(params["parent"])
    keep = bool(params.get("keep_transform", True))
    if keep:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    else:
        obj.parent = parent
    return serialize_object(obj)


@command("unparent_object")
def unparent_object(params: dict[str, Any]) -> dict[str, Any]:
    obj = get_object(params["name"])
    if params.get("keep_transform", True) and obj.parent:
        mw = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = mw
    else:
        obj.parent = None
    return serialize_object(obj)


@command("join_objects")
def join_objects(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    names = params["names"]
    if len(names) < 2:
        raise ValueError("join_objects requires at least two names")
    target_name = params.get("target") or names[0]
    target = get_object(target_name)
    bpy.ops.object.select_all(action="DESELECT")
    for name in names:
        get_object(name).select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    return serialize_object(bpy.context.view_layer.objects.active)


@command("separate_objects")
def separate_objects(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    obj = get_object(params["name"])
    active_select(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    mode = params.get("mode") or "LOOSE"
    type_map = {"LOOSE": "LOOSE", "SELECTED": "SELECTED", "MATERIAL": "MATERIAL"}
    bpy.ops.mesh.separate(type=type_map.get(mode, "LOOSE"))
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"selected": [o.name for o in bpy.context.selected_objects]}


@command("delete_object")
def delete_object(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    if not params.get("confirmed", False):
        raise PermissionError("delete_object requires confirmed=true")
    obj = get_object(params["name"])
    name = obj.name
    bpy.data.objects.remove(obj, do_unlink=True)
    return {"deleted": name}


@command("delete_objects")
def delete_objects(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    if not params.get("confirmed", False):
        raise PermissionError("delete_objects requires confirmed=true")
    deleted = []
    for name in params["names"]:
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise ValueError(f"OBJECT_NOT_FOUND:{name}")
        bpy.data.objects.remove(obj, do_unlink=True)
        deleted.append(name)
    return {"deleted": deleted}


@command("apply_transform")
def apply_transform(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    obj = get_object(params["name"])
    active_select(obj)
    bpy.ops.object.transform_apply(
        location=bool(params.get("location", True)),
        rotation=bool(params.get("rotation", True)),
        scale=bool(params.get("scale", True)),
    )
    return serialize_object(obj)


@command("reset_transform")
def reset_transform(params: dict[str, Any]) -> dict[str, Any]:
    import mathutils

    obj = get_object(params["name"])
    if params.get("location", True):
        obj.location = mathutils.Vector((0, 0, 0))
    if params.get("rotation", True):
        obj.rotation_euler = mathutils.Euler((0, 0, 0))
    if params.get("scale", True):
        obj.scale = mathutils.Vector((1, 1, 1))
    return serialize_object(obj)
