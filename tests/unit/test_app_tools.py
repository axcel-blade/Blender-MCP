from pathlib import Path

from blender_mcp.tools import app


def test_find_blender_uses_configured_path(tmp_path: Path) -> None:
    exe = tmp_path / "blender.exe"
    exe.write_text("")
    assert app.find_blender(str(exe)) == str(exe)


def test_find_blender_missing_configured_path(tmp_path: Path) -> None:
    assert app.find_blender(str(tmp_path / "nope.exe")) is None


def test_blend_file_tool_registered_in_core() -> None:
    from blender_mcp.tools.registry import CORE_TOOLS

    assert {"blend_file", "open_blender", "close_blender"} <= CORE_TOOLS


# --- server tools with a fake bridge -------------------------------------------------

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402

from blender_mcp.config import Settings  # noqa: E402
from blender_mcp.server import create_server  # noqa: E402
from blender_mcp.tools import files, status  # noqa: E402


def _run(mcp, name, **kw):
    r = asyncio.run(mcp.call_tool(name, kw))
    blocks = r[0] if isinstance(r, tuple) else r
    return json.loads(blocks[0].text)


@pytest.fixture
def fake_bridge(monkeypatch):
    sent: list[tuple[str, dict]] = []
    replies: dict[str, dict] = {}

    async def call(ctx, command, params=None, *, group=None):
        sent.append((command, params or {}))
        return replies.get(command, {"success": True, "result": {}})

    monkeypatch.setattr(files, "call_blender", call)
    monkeypatch.setattr(app, "call_blender", call)
    return sent, replies


def test_blend_file_requires_path(fake_bridge):
    out = _run(create_server(Settings()), "blend_file", action="save_as")
    assert out["success"] is False and "needs a path" in out["error"]
    assert fake_bridge[0] == []


def test_rename_bare_name_checked_against_allowed_dirs(fake_bridge, tmp_path):
    sent, replies = fake_bridge
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    replies["blend_file_info"] = {
        "success": True,
        "result": {"path": str(tmp_path / "outside" / "scene.blend")},
    }
    mcp = create_server(Settings(allowed_directories=[str(allowed)]))
    out = _run(mcp, "blend_file", action="rename", path="renamed")
    assert out["success"] is False
    assert [c for c, _ in sent] == ["blend_file_info"]  # never renamed

    replies["blend_file_info"]["result"]["path"] = str(allowed / "scene.blend")
    out = _run(mcp, "blend_file", action="rename", path="renamed")
    assert out["success"] is True
    assert sent[-1] == ("rename_blend_file", {"new_name": "renamed", "keep_old": False})


def test_save_copy_outside_allowed_dirs_refused(fake_bridge, tmp_path):
    mcp = create_server(Settings(allowed_directories=[str(tmp_path / "allowed")]))
    out = _run(mcp, "blend_file", action="save_copy", path=str(tmp_path / "x.blend"))
    assert out["success"] is False
    assert fake_bridge[0] == []


def test_open_passes_discard_flag(fake_bridge, tmp_path):
    f = tmp_path / "a.blend"
    f.write_bytes(b"x")
    _run(create_server(Settings()), "blend_file", action="open", path=str(f))
    assert fake_bridge[0][-1] == (
        "open_blend_file",
        {"path": str(f), "check_unsaved": True, "discard_changes": False},
    )


def test_open_blender_noop_when_running(monkeypatch):
    async def up(ctx):
        return True

    monkeypatch.setattr(app, "_bridge_up", up)
    out = _run(create_server(Settings()), "open_blender")
    assert out["result"] == {"already_running": True, "launched": False}


def test_open_blender_reports_missing_executable(monkeypatch):
    async def down(ctx):
        return False

    monkeypatch.setattr(app, "_bridge_up", down)
    monkeypatch.setattr(app, "find_blender", lambda configured="", version="": None)
    out = _run(create_server(Settings()), "open_blender")
    assert out["error_code"] == "BLENDER_NOT_FOUND"


def test_close_blender_relays_refusal(fake_bridge, monkeypatch):
    sent, replies = fake_bridge

    async def up(ctx):
        return True

    monkeypatch.setattr(app, "_bridge_up", up)
    replies["quit_blender"] = {"success": False, "error": "unsaved changes"}
    out = _run(create_server(Settings()), "close_blender")
    assert out["success"] is False
    assert sent[-1] == ("quit_blender", {"save": False, "discard_changes": False})


def test_outdated_addon_warns_about_file_commands():
    warnings = status.addon_warnings({"commands": ["import_local_asset", "lookup_api"]})
    assert any("quit_blender" in w and "rename_blend_file" in w for w in warnings)
    current = status.addon_warnings({"commands": list(status.REQUIRED_COMMANDS)})
    assert current == []


class _Proc:
    pid = 4242

    def poll(self):
        return None


def test_open_blender_does_not_relaunch_while_starting(monkeypatch):
    async def down(ctx):
        return False

    monkeypatch.setattr(app, "_bridge_up", down)
    monkeypatch.setattr(app, "_launched", _Proc())
    monkeypatch.setattr(app, "find_blender", lambda *a, **k: pytest.fail("relaunched"))
    out = _run(create_server(Settings()), "open_blender")
    assert out["result"]["starting"] is True


def test_open_blender_unknown_version(monkeypatch):
    async def down(ctx):
        return False

    monkeypatch.setattr(app, "_bridge_up", down)
    monkeypatch.setattr(app, "list_installs", lambda: [{"path": "x", "version": "5.3"}])
    out = _run(create_server(Settings()), "open_blender", version="4.2")
    assert out["error_code"] == "BLENDER_VERSION_NOT_FOUND"
    assert out["details"]["installs"][0]["version"] == "5.3"


def test_open_blender_list_installs_only(monkeypatch):
    monkeypatch.setattr(app, "list_installs", lambda: [{"path": "x", "version": "5.3"}])
    out = _run(create_server(Settings()), "open_blender", list_installs_only=True)
    assert out["result"]["installs"] == [{"path": "x", "version": "5.3"}]


def test_addon_status_reports_starting(monkeypatch):
    monkeypatch.setattr(app, "_launched", _Proc())
    out = _run(create_server(Settings()), "get_addon_status")
    assert out["result"]["blender"] == "starting"


def test_recover_skips_path_allow_list(fake_bridge, tmp_path):
    sent, _ = fake_bridge
    mcp = create_server(Settings(allowed_directories=[str(tmp_path / "allowed")]))
    out = _run(mcp, "blend_file", action="recover", path=str(tmp_path / "x_autosave.blend"))
    assert out["success"] is True
    assert sent[-1][0] == "recover_blend_file"


def test_recent_and_autosaves_map_to_commands(fake_bridge):
    sent, _ = fake_bridge
    mcp = create_server(Settings())
    _run(mcp, "blend_file", action="recent")
    _run(mcp, "blend_file", action="autosaves")
    assert [c for c, _ in sent] == ["recent_blend_files", "list_autosaves"]


def test_close_then_reopen_last_file(fake_bridge, monkeypatch, tmp_path):
    sent, replies = fake_bridge
    scene = tmp_path / "scene.blend"
    scene.write_bytes(b"x")
    state = {"up": True}

    async def bridge_up(ctx):
        return state["up"]

    async def no_disconnect():
        return None

    launched: list[list[str]] = []

    class Proc:
        pid = 1
        returncode = None

        def poll(self):
            return None

    def fake_popen(args, **kwargs):
        launched.append(args)
        return Proc()

    monkeypatch.setattr(app, "_bridge_up", bridge_up)
    monkeypatch.setattr(app, "_last_file", None)
    monkeypatch.setattr(app, "find_blender", lambda *a, **k: "blender.exe")
    monkeypatch.setattr(app.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(app, "blender_version", lambda exe: "5.3")
    mcp = create_server(Settings())
    monkeypatch.setattr(
        "blender_mcp.protocol.client.BlenderBridgeClient.disconnect",
        lambda self: no_disconnect(),
    )

    out = _run(mcp, "open_blender", reopen_last=True)
    assert out["error_code"] == "NO_LAST_FILE"

    replies["quit_blender"] = {"success": True, "result": {"filepath": str(scene)}}
    out = _run(mcp, "close_blender")
    assert out["result"]["file"] == str(scene)

    state["up"] = False
    monkeypatch.setattr(app, "_launched", None)
    out = _run(mcp, "open_blender", reopen_last=True, wait=False)
    assert out["success"] is True
    assert launched == [["blender.exe", str(scene)]]
