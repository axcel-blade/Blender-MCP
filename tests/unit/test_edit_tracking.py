"""Manual-edit tracking: snapshot diffing, dispatch wiring, and server pass-through."""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from blender_mcp.config import BridgeConfig
from blender_mcp.exceptions import BlenderMCPError
from blender_mcp.protocol.client import BlenderBridgeClient
from blender_mcp.protocol.messages import BridgeResponse

ROOT = Path(__file__).resolve().parents[2]


def _load_addon_module(name: str):
    if "blender_addon" not in sys.modules:
        pkg = types.ModuleType("blender_addon")
        pkg.__path__ = [str(ROOT / "blender_addon")]
        sys.modules["blender_addon"] = pkg
    full = f"blender_addon.{name}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, ROOT / "blender_addon" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


tracker = _load_addon_module("edit_tracker")
bridge = _load_addon_module("bridge_server")


def _obj(**kw):
    base = {"type": "MESH", "location": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 0.0),
            "scale": (1.0, 1.0, 1.0), "parent": None, "data": "Cube", "hidden": False,
            "hide_render": False, "materials": ("Material",), "modifiers": (),
            "collections": ("Collection",), "geometry": (8, 12, 6)}
    base.update(kw)
    return base


def _scene(**kw):
    base = {"scene": "Scene", "objects": {"Cube": _obj(), "Light": _obj(type="LIGHT")},
            "selected": ["Cube"], "active": "Cube", "mode": "OBJECT", "frame": 1,
            "materials": ["Material"]}
    base.update(kw)
    return base


# --- diff ---------------------------------------------------------------------------


def test_no_change_is_empty():
    assert tracker.diff(_scene(), _scene()) == {}


def test_moved_object_reports_new_transform():
    after = _scene()
    after["objects"]["Cube"] = _obj(location=(2.0, 0.0, 1.0))
    report = tracker.diff(_scene(), after)
    assert report["changed_objects"]["items"] == [
        {"name": "Cube", "changed": ["location"], "location": [2.0, 0.0, 1.0]}
    ]


def test_geometry_modifier_and_material_edits():
    after = _scene(materials=["Material", "Red"])
    after["objects"]["Cube"] = _obj(geometry=(10, 15, 7), modifiers=("Bevel",),
                                    materials=("Red",))
    report = tracker.diff(_scene(), after)
    assert report["changed_objects"]["items"][0]["changed"] == [
        "geometry", "materials", "modifiers"]
    assert report["added_materials"]["items"] == ["Red"]


def test_added_removed_selection_mode_frame():
    before = _scene()
    after = copy.deepcopy(before)
    del after["objects"]["Light"]
    after["objects"]["Suzanne"] = _obj(data="Suzanne")
    after.update(selected=["Suzanne"], active="Suzanne", mode="EDIT_MESH", frame=24)
    report = tracker.diff(before, after)
    assert report["added_objects"]["items"] == ["Suzanne"]
    assert report["removed_objects"]["items"] == ["Light"]
    assert report["selected"] == ["Suzanne"]
    assert (report["active"], report["mode"], report["frame"]) == ("Suzanne", "EDIT_MESH", 24)


def test_scene_switch_reported_alone():
    assert tracker.diff(_scene(), _scene(scene="Other")) == {
        "scene_switched": {"from": "Scene", "to": "Other"}}


def test_long_lists_are_capped():
    after = _scene()
    for i in range(tracker.MAX_REPORTED + 7):
        after["objects"][f"Obj{i:03}"] = _obj()
    report = tracker.diff(_scene(), after)
    assert len(report["added_objects"]["items"]) == tracker.MAX_REPORTED
    assert report["added_objects"]["more"] == 7


def test_collect_empty_before_first_baseline():
    tracker.reset()
    assert tracker.collect() == {}


# --- dispatch wiring ----------------------------------------------------------------


@pytest.fixture
def dispatch_env(monkeypatch):
    calls: list[str] = []
    fake = types.ModuleType("blender_addon.edit_tracker")
    fake.collect = lambda: calls.append("collect") or {"added_objects": {"items": ["Suzanne"]}}
    fake.rebaseline = lambda: calls.append("rebaseline")
    monkeypatch.setitem(sys.modules, "blender_addon.edit_tracker", fake)
    monkeypatch.setattr(sys.modules["blender_addon"], "edit_tracker", fake, raising=False)

    handlers = types.ModuleType("blender_addon.handlers")
    handlers.dispatch = lambda c, p: calls.append(c) or {"success": True, "result": "ok"}
    monkeypatch.setitem(sys.modules, "blender_addon.handlers", handlers)
    monkeypatch.setattr(bridge.execution_queue, "run_on_main_thread",
                        lambda func, timeout, should_run=None: func())
    monkeypatch.setattr(bridge, "log", lambda m: None)
    return calls, fake, handlers


def test_edits_collected_before_and_rebaselined_after(dispatch_env, monkeypatch):
    calls, _, _ = dispatch_env
    monkeypatch.setattr(bridge, "_prefs", lambda: None)
    resp = bridge._dispatch_request({"id": "1", "command": "get_scene_info"})
    assert calls == ["collect", "get_scene_info", "rebaseline"]
    assert resp["user_edits"] == {"added_objects": {"items": ["Suzanne"]}}
    assert resp["result"] == "ok"


def test_no_user_edits_key_when_nothing_changed(dispatch_env, monkeypatch):
    _, fake, _ = dispatch_env
    fake.collect = lambda: {}
    monkeypatch.setattr(bridge, "_prefs", lambda: None)
    assert "user_edits" not in bridge._dispatch_request({"id": "1", "command": "x"})


def test_rebaseline_even_when_command_raises(dispatch_env, monkeypatch):
    calls, _, handlers = dispatch_env

    def boom(c, p):
        raise RuntimeError("script failed")

    handlers.dispatch = boom
    monkeypatch.setattr(bridge, "_prefs", lambda: None)
    resp = bridge._dispatch_request({"id": "1", "command": "x"})
    assert resp["success"] is False
    assert calls[-1] == "rebaseline"


def test_tracker_failure_never_fails_command(dispatch_env, monkeypatch):
    _, fake, _ = dispatch_env

    def broken():
        raise RuntimeError("tracker bug")

    fake.collect = broken
    fake.rebaseline = broken
    monkeypatch.setattr(bridge, "_prefs", lambda: None)
    resp = bridge._dispatch_request({"id": "1", "command": "x"})
    assert resp["success"] is True and "user_edits" not in resp


def test_tracking_can_be_turned_off(dispatch_env, monkeypatch):
    calls, _, _ = dispatch_env
    monkeypatch.setattr(bridge, "_prefs", lambda: types.SimpleNamespace(
        track_user_edits=False, execution_timeout=60.0))
    resp = bridge._dispatch_request({"id": "1", "command": "x"})
    assert calls == ["x"] and "user_edits" not in resp


# --- server pass-through ------------------------------------------------------------


def test_response_carries_user_edits_to_tool_result():
    edits = {"changed_objects": {"items": [{"name": "Cube", "changed": ["location"]}]}}
    resp = BridgeResponse.from_dict({"id": "1", "success": True, "result": 1,
                                     "user_edits": edits})
    assert resp.to_tool_result()["user_edits"] == edits
    plain = BridgeResponse.from_dict({"id": "1", "success": True, "result": 1})
    assert "user_edits" not in plain.to_tool_result()


async def test_user_edits_kept_on_error_replies():
    client = BlenderBridgeClient(BridgeConfig(response_grace=0))
    sent: list[dict] = []
    client._connected = True
    client._writer = MagicMock()
    client._writer.write = MagicMock(side_effect=lambda raw: sent.append(json.loads(raw)))
    client._writer.drain = AsyncMock()

    async def reply():
        while not sent:
            await asyncio.sleep(0.001)
        await client._handle_incoming({
            "type": "response", "id": sent[0]["id"], "success": False,
            "error_code": "OBJECT_NOT_FOUND", "error": "Object not found: Cube",
            "user_edits": {"removed_objects": {"items": ["Cube"]}},
        })

    task = asyncio.create_task(reply())
    with pytest.raises(BlenderMCPError) as exc_info:
        await client.send_command("get_object_info", {"name": "Cube"})
    await task
    assert exc_info.value.details["user_edits"] == {"removed_objects": {"items": ["Cube"]}}
