"""Live Blender Python API lookup, read from the running Blender's own RNA.

Answers always match the user's Blender version: property names, types, enum
identifiers, defaults, operator arguments and node sockets. Read-only, except that
node lookups add a node to a temporary node group that is removed straight away.
"""

from __future__ import annotations

import contextlib
import importlib
import inspect
from typing import Any

from . import command

MAX_SEARCH_RESULTS = 50
MAX_ENUM_ITEMS = 80

# Node class prefix -> node tree type used to instantiate it for socket info.
_NODE_TREES = (
    ("ShaderNode", "ShaderNodeTree"),
    ("GeometryNode", "GeometryNodeTree"),
    ("FunctionNode", "GeometryNodeTree"),
    ("CompositorNode", "CompositorNodeTree"),
    ("TextureNode", "TextureNodeTree"),
)


def _jsonable_default(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    try:
        return [_jsonable_default(v) for v in value]
    except TypeError:
        return repr(value)


def describe_property(prop: Any) -> dict[str, Any]:
    info: dict[str, Any] = {
        "identifier": prop.identifier,
        "type": prop.type,
        "description": prop.description,
    }
    if prop.is_readonly:
        info["readonly"] = True
    subtype = getattr(prop, "subtype", "NONE")
    if subtype and subtype != "NONE":
        info["subtype"] = subtype
    if prop.type == "ENUM":
        items = list(prop.enum_items)
        info["enum_items"] = [i.identifier for i in items[:MAX_ENUM_ITEMS]]
        if len(items) > MAX_ENUM_ITEMS:
            info["enum_items_truncated"] = len(items)
        if getattr(prop, "is_enum_flag", False):
            info["enum_flag"] = True
        if not items:
            info["note"] = "Items depend on context; read them from a live instance."
    elif prop.type in ("POINTER", "COLLECTION"):
        fixed = getattr(prop, "fixed_type", None)
        if fixed is not None:
            info["fixed_type"] = fixed.identifier
    else:
        length = getattr(prop, "array_length", 0)
        if length:
            info["array_length"] = length
            info["default"] = _jsonable_default(getattr(prop, "default_array", None))
        elif hasattr(prop, "default"):
            info["default"] = _jsonable_default(prop.default)
        for key in ("hard_min", "hard_max"):
            if hasattr(prop, key):
                info[key.replace("hard_", "")] = _jsonable_default(getattr(prop, key))
    return info


def _describe_function(func: Any) -> dict[str, Any]:
    params = [describe_property(p) for p in func.parameters if not p.is_output]
    outputs = [describe_property(p) for p in func.parameters if p.is_output]
    info: dict[str, Any] = {
        "identifier": func.identifier,
        "description": func.description,
        "parameters": params,
    }
    if outputs:
        info["returns"] = outputs
    return info


def describe_struct(rna: Any, cls: Any = None) -> dict[str, Any]:
    base = rna.base
    props = [describe_property(p) for p in rna.properties if p.identifier != "rna_type"]
    info: dict[str, Any] = {
        "kind": "struct",
        "identifier": rna.identifier,
        "description": rna.description,
        "base": base.identifier if base is not None else None,
        "properties": props,
        "functions": [_describe_function(f) for f in rna.functions],
    }
    if cls is not None:
        info["python_methods"] = sorted(
            n for n, v in vars(cls).items() if callable(v) and not n.startswith("_")
        )
    return info


def _node_tree_type(identifier: str) -> str | None:
    for prefix, tree in _NODE_TREES:
        if identifier.startswith(prefix):
            return tree
    return None


def _socket(sock: Any) -> dict[str, Any]:
    info: dict[str, Any] = {
        "name": sock.name,
        "identifier": sock.identifier,
        "type": sock.type,
    }
    if hasattr(sock, "default_value"):
        info["default"] = _jsonable_default(sock.default_value)
    if not getattr(sock, "enabled", True):
        info["enabled"] = False
    return info


def describe_node(identifier: str) -> dict[str, Any] | None:
    """Sockets of a node type, read from a throwaway instance."""
    import bpy

    tree_type = _node_tree_type(identifier)
    if tree_type is None:
        return None
    tree = None
    try:
        tree = bpy.data.node_groups.new("__mcp_api_lookup__", tree_type)
        node = tree.nodes.new(identifier)
        return {
            "type": node.type,
            "tree_type": tree_type,
            "inputs": [_socket(s) for s in node.inputs],
            "outputs": [_socket(s) for s in node.outputs],
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Could not instantiate {identifier} in {tree_type}: {exc}"}
    finally:
        if tree is not None:
            bpy.data.node_groups.remove(tree)


def _live_instances() -> list[Any]:
    """A few always-available datablocks to read dynamic enum values from."""
    import bpy

    ctx = bpy.context
    scene = getattr(ctx, "scene", None)
    found: list[Any] = []
    for obj in (scene, getattr(ctx, "object", None), getattr(ctx, "preferences", None),
                getattr(scene, "world", None)):
        if obj is not None:
            found.append(obj)
    if scene is not None:
        for attr in ("render", "cycles", "eevee", "view_settings", "display_settings",
                     "display", "tool_settings", "unit_settings", "sequencer_colorspace_settings"):
            sub = getattr(scene, attr, None)
            if sub is not None:
                found.append(sub)
    return found


def parse_enum_error(message: str) -> list[str] | None:
    """Valid identifiers from a "enum "x" not found in ('A', 'B')" TypeError."""
    import ast

    start = message.find(" in (")
    if start < 0:
        return None
    try:
        values = ast.literal_eval(message[start + 4:].strip())
    except (ValueError, SyntaxError):
        return None
    if isinstance(values, str):
        values = (values,)
    return [str(v) for v in values] if isinstance(values, tuple) else None


def live_enum_items(type_name: str, prop: str) -> list[str] | None:
    """Read a dynamic enum's real values by assigning an invalid one (it is rejected,
    so nothing changes) on a live instance of ``type_name``."""
    for inst in _live_instances():
        rna = getattr(inst, "bl_rna", None)
        if rna is None or rna.identifier != type_name or prop not in rna.properties:
            continue
        if rna.properties[prop].is_readonly:
            return None
        try:
            setattr(inst, prop, "__mcp_invalid__")
        except TypeError as exc:
            return parse_enum_error(str(exc))
        except Exception:  # noqa: BLE001
            return None
    return None


def _lookup_type(name: str, member: str | None) -> dict[str, Any] | None:
    import bpy

    cls = getattr(bpy.types, name, None)
    if cls is None or not hasattr(cls, "bl_rna"):
        # Add-on property groups (e.g. CyclesRenderSettings) aren't in bpy.types.
        inst = next(
            (i for i in _live_instances() if getattr(i, "bl_rna", None)
             and i.bl_rna.identifier == name),
            None,
        )
        if inst is None:
            return None
        cls = type(inst)
    rna = cls.bl_rna
    if member:
        if member in rna.properties:
            info = {"kind": "property", "owner": name, **describe_property(rna.properties[member])}
            if info["type"] == "ENUM":
                live = live_enum_items(name, member)
                if live is not None and live != info.get("enum_items"):
                    # Dynamic enums (render engines, etc.) under-report on the class.
                    info["enum_items"] = live
                    info["enum_items_source"] = "live instance"
            return info
        if member in rna.functions:
            return {"kind": "function", "owner": name, **_describe_function(rna.functions[member])}
        attr = getattr(cls, member, None)
        if attr is not None:
            return _python_object(f"bpy.types.{name}.{member}", attr)
        return {
            "kind": "missing",
            "identifier": f"bpy.types.{name}.{member}",
            "error": f"{name} has no member {member!r}.",
            "close_matches": _close(member, [p.identifier for p in rna.properties]
                                    + [f.identifier for f in rna.functions]),
        }
    info = describe_struct(rna, cls)
    if issubclass(cls, bpy.types.Node):
        node = describe_node(name)
        if node:
            info["node"] = node
    return info


def _lookup_operator(path: str) -> dict[str, Any] | None:
    import bpy

    parts = path.split(".")
    if len(parts) != 2:
        return None
    module = getattr(bpy.ops, parts[0], None)
    if module is None:
        return None
    try:
        op = getattr(module, parts[1])
        rna = op.get_rna_type()
    except (AttributeError, KeyError, RuntimeError):
        return None
    return {
        "kind": "operator",
        "identifier": f"bpy.ops.{path}",
        "idname": op.idname(),
        "description": rna.description,
        "parameters": [describe_property(p) for p in rna.properties if p.identifier != "rna_type"],
        "note": "Operators depend on mode, active object and selection; "
        "use bpy.context.temp_override(...) or the bpy.data API.",
    }


def _python_object(identifier: str, obj: Any) -> dict[str, Any]:
    info: dict[str, Any] = {"kind": "python", "identifier": identifier}
    with contextlib.suppress(TypeError, ValueError):
        info["signature"] = str(inspect.signature(obj))
    doc = inspect.getdoc(obj)
    if doc:
        info["doc"] = doc[:4000]
    if inspect.ismodule(obj) or inspect.isclass(obj):
        info["members"] = sorted(n for n in dir(obj) if not n.startswith("_"))[:300]
    return info


def _lookup_python(identifier: str) -> dict[str, Any] | None:
    parts = identifier.split(".")
    for split in range(len(parts), 0, -1):
        try:
            obj: Any = importlib.import_module(".".join(parts[:split]))
        except ImportError:
            continue
        try:
            for attr in parts[split:]:
                obj = getattr(obj, attr)
        except AttributeError:
            return None
        return _python_object(identifier, obj)
    return None


def _close(word: str, candidates: list[str], limit: int = 8) -> list[str]:
    import difflib

    return difflib.get_close_matches(word, candidates, n=limit, cutoff=0.6)


def search(query: str, limit: int = 20) -> dict[str, Any]:
    """Types, properties and operators whose names contain every word of ``query``."""
    import bpy

    tokens = [t.lower() for t in query.replace(".", " ").split() if t]
    limit = max(1, min(int(limit), MAX_SEARCH_RESULTS))
    hits: list[dict[str, Any]] = []

    def matches(*texts: str) -> bool:
        blob = " ".join(texts).lower()
        return all(t in blob for t in tokens)

    for name in dir(bpy.types):
        cls = getattr(bpy.types, name, None)
        rna = getattr(cls, "bl_rna", None)
        if rna is None:
            continue
        if matches(name):
            hits.append({"kind": "struct", "identifier": f"bpy.types.{name}",
                         "description": rna.description})
        for prop in rna.properties:
            if prop.identifier != "rna_type" and matches(name, prop.identifier):
                hits.append({"kind": "property",
                             "identifier": f"bpy.types.{name}.{prop.identifier}",
                             "type": prop.type, "description": prop.description})
        if len(hits) >= limit * 4:
            break

    for mod_name in dir(bpy.ops):
        module = getattr(bpy.ops, mod_name, None)
        for op_name in dir(module):
            if matches(mod_name, op_name):
                hits.append({"kind": "operator", "identifier": f"bpy.ops.{mod_name}.{op_name}"})

    # Shortest identifiers first: exact-ish matches beat deep property paths.
    hits.sort(key=lambda h: (h["kind"] == "property", len(h["identifier"])))
    return {"kind": "search", "query": query, "count": len(hits[:limit]), "results": hits[:limit]}


def lookup(query: str) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        raise ValueError("Pass an identifier (bpy.types.Scene, bpy.ops.mesh.primitive_cube_add, "
                         "ShaderNodeBsdfPrincipled) or search words (bevel modifier width).")
    ident = query.removeprefix("bpy.types.")
    if " " not in query:
        if query.startswith("bpy.ops."):
            found = _lookup_operator(query.removeprefix("bpy.ops."))
            if found:
                return found
        elif "." not in ident or query.startswith("bpy.types."):
            name, _, member = ident.partition(".")
            found = _lookup_type(name, member or None)
            if found:
                return found
        else:
            found = _lookup_python(query)
            if found:
                return found
            name, _, member = ident.partition(".")
            found = _lookup_type(name, member or None)
            if found:
                return found
    result = search(query)
    if not result["results"]:
        result["hint"] = "No match. Try fewer or different words, or an exact type name."
    return result


@command("lookup_api")
def lookup_api(params: dict[str, Any]) -> dict[str, Any]:
    import bpy

    result = lookup(str(params.get("query", "")))
    result["blender_version"] = bpy.app.version_string
    return result
