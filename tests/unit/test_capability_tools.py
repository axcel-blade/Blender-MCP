"""Capability-expansion tools: registration, server/addon command parity, dispatcher history,
path validation and pure helpers. Runs without Blender (handlers import bpy lazily)."""

from __future__ import annotations

import asyncio
import importlib
import re
import sys
import types
from pathlib import Path

import pytest

from blender_mcp.config import load_settings
from blender_mcp.server import create_server
from blender_mcp.tools.registry import AppContext, call_blender_paths, forward_params

ROOT = Path(__file__).resolve().parents[2]

NEW_HANDLER_MODULES = (
    "analysis",
    "animation_advanced",
    "compositing",
    "grease_pencil",
    "library",
    "modeling",
    "physics",
    "render_config",
    "rigging",
    "scene_builder",
    "sculpting",
    "shading",
    "uv",
    "video_editing",
    "world",
)

NEW_TOOLS = {
    "sculpt_deform",
    "set_sculpt_brush",
    "voxel_remesh",
    "uv_unwrap",
    "create_armature",
    "setup_ik_chain",
    "bind_mesh_to_armature",
    "set_vertex_weights",
    "validate_rig",
    "animate_property",
    "set_keyframe_interpolation",
    "make_animation_cyclic",
    "bake_animation",
    "add_rigid_body",
    "add_cloth",
    "add_fluid",
    "add_particle_system",
    "add_force_field",
    "fracture_object",
    "bake_simulation",
    "configure_cycles",
    "configure_eevee",
    "configure_render_passes",
    "batch_render",
    "create_studio_lighting",
    "analyze_lighting",
    "create_camera_rig",
    "apply_compositor_effect",
    "vse_add_strip",
    "vse_add_transition",
    "create_grease_pencil",
    "draw_grease_pencil_stroke",
    "set_hdri_environment",
    "set_sky",
    "create_terrain",
    "create_water",
    "scatter_objects",
    "generate_environment",
    "create_room",
    "create_castle",
    "create_city",
    "create_product_shot",
    "create_data_visualization",
    "boolean_operation",
    "loop_cut",
    "create_gn_scatter",
    "create_procedural_material",
    "set_pbr_textures",
    "analyze_scene",
    "check_3d_print",
    "prepare_for_3d_print",
    "check_game_asset",
    "export_for_engine",
    "mark_as_asset",
    "append_from_blend",
    "pack_resources",
    "list_addons",
    "set_addon_enabled",
    "create_checkpoint",
    "undo",
    "get_execution_history",
    "batch_apply",
    "run_workflow",
    "track_camera_motion",
}


@pytest.fixture(scope="module")
def handlers():
    """Load the real addon handler package in isolation.

    Other tests install stub ``blender_addon`` packages in ``sys.modules``; snapshot and
    restore them so neither side sees the other's modules.
    """
    saved = {
        k: v
        for k, v in sys.modules.items()
        if k == "blender_addon" or k.startswith("blender_addon.")
    }
    for key in saved:
        del sys.modules[key]
    pkg = types.ModuleType("blender_addon")
    pkg.__path__ = [str(ROOT / "blender_addon")]
    sys.modules["blender_addon"] = pkg
    try:
        module = importlib.import_module("blender_addon.handlers")
        for name in module._HANDLER_MODULES:  # noqa: SLF001
            importlib.import_module(f"blender_addon.handlers.{name}")
        yield module
    finally:
        for key in [
            k for k in sys.modules if k == "blender_addon" or k.startswith("blender_addon.")
        ]:
            del sys.modules[key]
        sys.modules.update(saved)


@pytest.fixture(scope="module")
def tool_names():
    settings = load_settings()
    settings.tool_profile = "full"
    mcp = create_server(settings)
    return set(mcp._tool_manager._tools)  # noqa: SLF001


def test_new_tools_registered_in_full_profile(tool_names):
    missing = NEW_TOOLS - tool_names
    assert not missing, f"missing tools: {sorted(missing)}"


def test_core_profile_still_small():
    settings = load_settings()
    settings.tool_profile = "core"
    mcp = create_server(settings)
    names = set(mcp._tool_manager._tools)  # noqa: SLF001
    assert not (names & NEW_TOOLS)


def test_every_server_command_has_an_addon_handler(handlers):
    registered = set(handlers._REGISTRY)  # noqa: SLF001
    pattern = re.compile(r'call_blender(?:_paths)?\(\s*ctx,\s*"([a-z0-9_]+)"')
    sent = set()
    for path in (ROOT / "src" / "blender_mcp" / "tools").glob("*.py"):
        sent |= set(pattern.findall(path.read_text(encoding="utf-8")))
    missing = sorted(sent - registered)
    assert not missing, f"server sends commands the addon does not handle: {missing}"


def test_handler_modules_listed_for_reload(handlers):
    for name in NEW_HANDLER_MODULES:
        assert name in handlers._HANDLER_MODULES  # noqa: SLF001


def test_dispatch_records_history_and_errors(handlers):
    handlers._REGISTRY["_test_ok"] = lambda p: {"value": p.get("x")}  # noqa: SLF001
    handlers._REGISTRY["_test_bad"] = lambda p: (_ for _ in ()).throw(ValueError("nope"))  # noqa: SLF001
    try:
        ok = handlers.dispatch("_test_ok", {"x": 3})
        bad = handlers.dispatch("_test_bad", {"long": "y" * 500})
    finally:
        handlers._REGISTRY.pop("_test_ok")  # noqa: SLF001
        handlers._REGISTRY.pop("_test_bad")  # noqa: SLF001
    assert ok == {"success": True, "result": {"value": 3}}
    assert bad["success"] is False and bad["error_code"] == "INVALID_PARAMETER"
    last = list(handlers.history())[-2:]
    assert [h["command"] for h in last] == ["_test_ok", "_test_bad"]
    assert last[1]["success"] is False and last[1]["error"] == "nope"
    assert len(last[1]["params"]["long"]) <= 120  # params are summarised, not stored whole


def test_batch_and_workflow_refuse_code_execution(handlers):
    library = importlib.import_module("blender_addon.handlers.library")
    with pytest.raises(PermissionError):
        library.batch_apply({"command": "execute_blender_code", "objects": []})
    report = library.run_workflow(
        {"steps": [{"command": "execute_blender_code", "params": {}}], "checkpoint": False}
    )
    assert report["failed"] == 1 and report["stopped_at"] == 0


def test_kelvin_to_rgb_is_warm_to_cool(handlers):
    rc = importlib.import_module("blender_addon.handlers.render_config")
    warm, daylight, cool = rc.kelvin_to_rgb(2700), rc.kelvin_to_rgb(6500), rc.kelvin_to_rgb(12000)
    assert warm[0] >= warm[2] and cool[2] >= cool[0]
    assert all(0.9 <= c <= 1.0 for c in daylight)


def test_forward_params_drops_ctx_and_none():
    assert forward_params({"ctx": 1, "a": 0, "b": None, "c": False}) == {"a": 0, "c": False}


def test_path_tools_respect_allowed_directories(tmp_path):
    settings = load_settings()
    settings.allowed_directories = [str(tmp_path / "allowed")]

    class Bridge:
        called = False

        async def send_command(self, command, params):
            Bridge.called = True
            return {"success": True}

    ctx = AppContext(settings, Bridge())  # type: ignore[arg-type]
    outside = tmp_path / "elsewhere" / "sky.hdr"
    res = asyncio.run(
        call_blender_paths(ctx, "set_hdri_environment", {"path": str(outside)}, group="environment")
    )
    assert res["success"] is False and not Bridge.called
    maps = {"base_color": str(outside)}
    res = asyncio.run(
        call_blender_paths(
            ctx, "set_pbr_textures", {"maps": maps}, group="materials", path_keys=("maps",)
        )
    )
    assert res["success"] is False and not Bridge.called


def test_disabled_group_blocks_tool(tmp_path):
    settings = load_settings()
    settings.tool_groups.physics = False

    class Bridge:
        async def send_command(self, command, params):
            raise AssertionError("must not reach Blender")

    ctx = AppContext(settings, Bridge())  # type: ignore[arg-type]
    from blender_mcp.tools.registry import call_blender

    res = asyncio.run(call_blender(ctx, "add_cloth", {"name": "Flag"}, group="physics"))
    assert res["success"] is False
