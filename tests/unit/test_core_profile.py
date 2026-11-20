import pytest

from blender_mcp.config import Settings
from blender_mcp.server import create_server
from blender_mcp.tools.registry import CORE_TOOLS


def _names(mcp):
    return {t.name for t in mcp._tool_manager.list_tools()}  # noqa: SLF001


def test_core_profile_is_default_and_small():
    names = _names(create_server(Settings()))
    assert names == set(CORE_TOOLS)
    assert len(names) <= 15


def test_full_profile_keeps_everything():
    names = _names(create_server(Settings(tool_profile="full")))
    assert names >= CORE_TOOLS
    assert len(names) > 100


def test_bad_profile_rejected():
    with pytest.raises(ValueError):
        Settings(tool_profile="huge")


def test_run_script_shared_namespace_and_tail_expression():
    import importlib.util
    import pathlib
    import sys
    import types

    root = pathlib.Path(__file__).resolve().parents[2]
    pkg = types.ModuleType("blender_addon")
    pkg.__path__ = [str(root / "blender_addon")]
    sys.modules.setdefault("blender_addon", pkg)
    handlers = types.ModuleType("blender_addon.handlers")
    handlers.__path__ = [str(root / "blender_addon" / "handlers")]
    handlers.command = lambda name: lambda fn: fn
    sys.modules["blender_addon.handlers"] = handlers
    spec = importlib.util.spec_from_file_location(
        "blender_addon.handlers.scripting", root / "blender_addon/handlers/scripting.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    code = "import math\ndef f(x):\n    return math.sqrt(x) + k\nk = 1\n{'v': f(9)}"
    assert mod.run_script(code) == {"v": 4.0}
    assert mod.run_script("result = (1, 2)\n3") == [1, 2]
    assert mod.run_script("x = 1") is None
