"""lookup_api: server wiring and the addon's RNA description helpers (no Blender)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest

from blender_mcp.config import Settings
from blender_mcp.server import create_server
from blender_mcp.tools.registry import CORE_TOOLS

ROOT = Path(__file__).resolve().parents[2]


def _load_api_docs():
    for name, path in (("blender_addon", ""), ("blender_addon.handlers", "handlers")):
        if name not in sys.modules:
            pkg = types.ModuleType(name)
            pkg.__path__ = [str(ROOT / "blender_addon" / path)]
            sys.modules[name] = pkg
    handlers = sys.modules["blender_addon.handlers"]
    if not hasattr(handlers, "command"):
        handlers.command = lambda name: (lambda f: f)
    spec = importlib.util.spec_from_file_location(
        "blender_addon.handlers.api_docs", ROOT / "blender_addon/handlers/api_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


api = _load_api_docs()


def _prop(**kw):
    base = dict(identifier="x", type="FLOAT", description="d", is_readonly=False,
                subtype="NONE", array_length=0, default=1.5, hard_min=0.0, hard_max=10.0)
    base.update(kw)
    return NS(**base)


def test_lookup_api_is_core():
    assert "lookup_api" in CORE_TOOLS
    names = {t.name for t in create_server(Settings())._tool_manager.list_tools()}  # noqa: SLF001
    assert "lookup_api" in names


@pytest.mark.asyncio
async def test_tool_forwards_query_to_addon():
    bridge = AsyncMock()
    bridge.send_command.return_value = {"success": True, "result": {"kind": "struct"}}
    import blender_mcp.tools.status as status

    ctx = NS(settings=Settings(), bridge=bridge)
    status.register(fake := NS(tool=lambda name: (lambda f: setattr(fake, name, f) or f),
                               resource=lambda uri: (lambda f: f)), ctx)
    result = await fake.lookup_api("Scene")
    bridge.send_command.assert_awaited_once_with("lookup_api", {"query": "Scene"})
    assert result["success"] is True


def test_describe_scalar_property():
    info = api.describe_property(_prop())
    assert info == {"identifier": "x", "type": "FLOAT", "description": "d",
                    "default": 1.5, "min": 0.0, "max": 10.0}


def test_describe_enum_property_lists_identifiers():
    items = [NS(identifier=f"E{i}") for i in range(3)]
    info = api.describe_property(_prop(type="ENUM", enum_items=items, is_enum_flag=False))
    assert info["enum_items"] == ["E0", "E1", "E2"]


def test_describe_enum_truncates_and_flags_dynamic():
    many = [NS(identifier=str(i)) for i in range(api.MAX_ENUM_ITEMS + 5)]
    info = api.describe_property(_prop(type="ENUM", enum_items=many))
    assert len(info["enum_items"]) == api.MAX_ENUM_ITEMS
    assert info["enum_items_truncated"] == api.MAX_ENUM_ITEMS + 5
    empty = api.describe_property(_prop(type="ENUM", enum_items=[]))
    assert "context" in empty["note"]


def test_describe_pointer_and_array():
    ptr = api.describe_property(_prop(type="POINTER", fixed_type=NS(identifier="Material")))
    assert ptr["fixed_type"] == "Material"
    arr = api.describe_property(_prop(array_length=3, default_array=(0.0, 1.0, 2.0),
                                      subtype="XYZ", is_readonly=True))
    assert arr["default"] == [0.0, 1.0, 2.0]
    assert arr["subtype"] == "XYZ" and arr["readonly"] is True


@pytest.mark.parametrize(
    ("ident", "tree"),
    [("ShaderNodeBsdfPrincipled", "ShaderNodeTree"),
     ("GeometryNodeMeshCube", "GeometryNodeTree"),
     ("FunctionNodeRandomValue", "GeometryNodeTree"),
     ("Object", None)],
)
def test_node_tree_type(ident, tree):
    assert api._node_tree_type(ident) == tree


def test_python_lookup_without_blender():
    info = api._lookup_python("json.dumps")
    assert info["kind"] == "python" and "obj" in info["signature"]
    assert api._lookup_python("json.no_such_thing") is None


def test_parse_enum_error():
    msg = (
        "bpy_struct: item.attr = val: enum \"__mcp_invalid__\" "
        "not found in ('BLENDER_EEVEE', 'CYCLES')"
    )
    assert api.parse_enum_error(msg) == ["BLENDER_EEVEE", "CYCLES"]
    assert api.parse_enum_error("enum \"x\" not found in ('ONLY')") == ["ONLY"]
    assert api.parse_enum_error("some other error") is None
