"""Safe execution mode: which scripts are refused, and that normal bpy code is not."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    if "blender_addon" not in sys.modules:
        pkg = types.ModuleType("blender_addon")
        pkg.__path__ = [str(ROOT / "blender_addon")]
        sys.modules["blender_addon"] = pkg
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


safety = _load("blender_addon.script_safety", "blender_addon/script_safety.py")


def refused(code: str) -> list[str]:
    return [v.what for v in safety.check(code)]


# --- refused ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "import subprocess\nsubprocess.run(['ls'])",
        "import os\nos.system('rm -rf /')",
        "import os as o\no.system('x')",
        "from os import system\nsystem('x')",
        "import os\nx = os\nx.popen('x')",
        "import os\nos.execv('/bin/sh', [])",
        "import os\nos.remove('a.blend')",
        "import shutil\nshutil.rmtree('C:/Users')",
        "from pathlib import Path\nPath('a.txt').unlink()",
        "import pathlib\npathlib.Path('d').rmdir()",
        "import socket",
        "import urllib.request\nurllib.request.urlopen('http://x')",
        "from http import client",
        "import requests",
        "bpy.utils.register_class(MyPanel)",
        "bpy.app.handlers.depsgraph_update_post.append(f)",
        "bpy.app.timers.register(f)",
        "import addon_utils\naddon_utils.enable('x')",
        "bpy.ops.preferences.addon_enable(module='x')",
        "bpy.ops.wm.save_userpref()",
        "bpy.context.preferences.view.ui_scale = 2.0",
        "C.preferences.filepaths.temporary_directory = '/tmp'",
        "p = bpy.context.preferences\np.view.ui_scale = 3",
        "bpy.ops.wm.quit_blender()",
        "bpy.ops.wm.read_factory_settings()",
        "ops = bpy.ops.wm\nops.read_homefile()",
        "eval('1+1')",
        "exec('x=1')",
        "compile('x', 'f', 'exec')",
        "__import__('os').system('x')",
        "import importlib\nimportlib.import_module('os')",
        "import ctypes",
        "().__class__.__bases__[0].__subclasses__()",
        "f.__globals__['os']",
        "getattr(f, '__globals__')",
        "import os\ngetattr(os, 'system')('x')",
        "getattr(bpy.ops.wm, 'quit_blender')()",
        "import builtins",
    ],
)
def test_dangerous_scripts_refused(code):
    assert refused(code), f"should be refused: {code!r}"


def test_violation_reports_line_and_reason():
    code = "x = 1\nimport os\n\nos.system('ls')"
    [v] = safety.check(code)
    assert v.line == 4 and v.what == "os.system" and v.reason == safety.PROCESS


def test_error_message_is_actionable():
    with pytest.raises(PermissionError) as exc_info:
        safety.enforce("import os\nos.system('x')\nbpy.ops.wm.quit_blender()")
    msg = str(exc_info.value)
    assert "line 2: os.system" in msg and "line 3: bpy.ops.wm.quit_blender" in msg
    assert "Safe execution mode" in msg


# --- allowed: everyday Blender scripting ---------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "bpy.ops.mesh.primitive_cube_add(size=2)",
        "obj = bpy.data.objects['Cube']\nobj.location = (1, 2, 3)",
        "coll = bpy.data.collections.new('X')\nbpy.context.scene.collection.children.link(coll)",
        "bpy.context.scene.collection.objects.unlink(obj)",
        "coll.objects.unlink(bpy.data.objects['Cube'])",
        "bpy.data.objects.remove(obj, do_unlink=True)",
        "import bmesh\nbm = bmesh.new()\nbmesh.ops.create_cube(bm, size=1)",
        "import mathutils\nv = mathutils.Vector((1, 0, 0))",
        "import math, random, json\nx = math.pi * random.random()",
        "import os\np = os.path.join(bpy.path.abspath('//'), 'tex.png')\nos.path.exists(p)",
        "import os\nfiles = os.listdir(bpy.path.abspath('//'))",
        "bpy.ops.wm.save_as_mainfile(filepath='//out.blend')",
        "bpy.ops.export_scene.gltf(filepath='//out.glb')",
        "bpy.context.scene.render.filepath = '//r.png'\nbpy.ops.render.render(write_still=True)",
        "prefs = bpy.context.preferences\nresult = prefs.view.ui_scale",
        "result = type(obj).__name__",
        "result = obj.__class__.__name__",
        "value = getattr(node.inputs, 'Base Color', None)",
        "setattr(obj, 'location', (0, 0, 0))",
        "result = [o.name for o in D.objects if o.type == 'MESH']",
        "mat = bpy.data.materials.new('Red')\nmat.use_nodes = True",
        "def f(x):\n    return x * 2\nresult = f(3)",
        "result = compile_count = 3",
    ],
)
def test_normal_blender_code_allowed(code):
    assert refused(code) == [], f"should be allowed: {code!r}"


def test_syntax_error_left_to_python():
    assert safety.check("def (:") == []


# --- wiring in the scripting handler ------------------------------------------------


@pytest.fixture
def scripting(monkeypatch):
    handlers = types.ModuleType("blender_addon.handlers")
    handlers.__path__ = [str(ROOT / "blender_addon" / "handlers")]
    handlers.command = lambda name: lambda f: f
    monkeypatch.setitem(sys.modules, "blender_addon.handlers", handlers)
    spec = importlib.util.spec_from_file_location(
        "blender_addon.handlers.scripting", ROOT / "blender_addon/handlers/scripting.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "blender_addon.handlers.scripting", module)
    spec.loader.exec_module(module)
    return module


def _prefs(safe: bool):
    return types.SimpleNamespace(script_permission="trusted", safe_execution_mode=safe)


def test_handler_refuses_before_running(scripting, monkeypatch):
    ran = []
    monkeypatch.setattr(scripting, "_prefs", lambda: _prefs(True))
    monkeypatch.setattr(scripting, "run_script", lambda code: ran.append(code))
    with pytest.raises(PermissionError, match="os.system"):
        scripting.execute_blender_code({"code": "import os\nos.system('x')"})
    assert ran == []


def test_handler_allows_when_safe_mode_off(scripting, monkeypatch):
    monkeypatch.setattr(scripting, "_prefs", lambda: _prefs(False))
    monkeypatch.setattr(scripting, "run_script", lambda code: "ran")
    out = scripting.execute_blender_code({"code": "import os\nos.system('x')"})
    assert out["success"] is True and out["result"] == "ran"


def test_preview_lists_refused_operations(scripting, monkeypatch):
    monkeypatch.setattr(scripting, "_prefs", lambda: _prefs(True))
    out = scripting.execute_blender_code(
        {"code": "bpy.ops.wm.quit_blender()", "preview_only": True}
    )
    assert out["refused_operations"] == [f"line 1: bpy.ops.wm.quit_blender ({safety.SESSION})"]
