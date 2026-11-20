"""Timeout handling: per-command timeouts, cancelling unstarted jobs, clear messages."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import socket
import sys
import threading
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from blender_mcp.config import BridgeConfig, load_settings
from blender_mcp.exceptions import BlenderMCPError, ErrorCode, TimeoutError_
from blender_mcp.protocol.client import BlenderBridgeClient
from blender_mcp.protocol.timeouts import (
    MAX_TIMEOUT,
    SLOW_COMMAND_TIMEOUTS,
    no_reply_message,
    resolve_timeout,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_addon_module(name: str):
    """Import blender_addon.<name> from source without Blender."""
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


eq = _load_addon_module("execution_queue")
bridge = _load_addon_module("bridge_server")


@pytest.fixture(autouse=True)
def _empty_queue():
    while not eq._JOB_QUEUE.empty():
        eq._JOB_QUEUE.get_nowait()
        eq._JOB_QUEUE.task_done()
    yield


# --- resolve_timeout -----------------------------------------------------------------


def test_default_used_for_ordinary_command():
    assert resolve_timeout("get_scene_info", {}, 60.0) == 60.0


def test_slow_commands_get_longer_defaults():
    expected = SLOW_COMMAND_TIMEOUTS["render_animation"]
    assert resolve_timeout("render_animation", {}, 60.0) == expected
    assert resolve_timeout("import_asset", {}, 60.0) > 60.0


def test_precedence_explicit_then_params_then_config_then_builtin():
    overrides = {"render_scene": 900.0}
    assert resolve_timeout("render_scene", {"timeout": 30}, 60, overrides, explicit=5) == 5
    assert resolve_timeout("render_scene", {"timeout": 30}, 60, overrides) == 30
    assert resolve_timeout("render_scene", {}, 60, overrides) == 900
    assert resolve_timeout("render_scene", {}, 60) == SLOW_COMMAND_TIMEOUTS["render_scene"]


@pytest.mark.parametrize("bad", [None, 0, -5, "abc", float("nan"), True])
def test_invalid_values_fall_through(bad):
    assert resolve_timeout("get_scene_info", {"timeout": bad}, 60.0) == 60.0


def test_clamped_to_maximum():
    assert resolve_timeout("x", {"timeout": 10**9}, 60.0) == MAX_TIMEOUT


def test_command_timeouts_loaded_from_toml(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("[bridge]\n[bridge.command_timeouts]\nrender_animation = 3000\n")
    settings = load_settings(cfg)
    assert settings.bridge().command_timeouts == {"render_animation": 3000.0}


def test_no_reply_message_is_actionable():
    msg = no_reply_message("render_scene", 600)
    assert "render_scene" in msg and "600s" in msg
    assert "before retrying" in msg


# --- server client ------------------------------------------------------------------


def _fake_connected_client(**config) -> tuple[BlenderBridgeClient, list[dict]]:
    client = BlenderBridgeClient(BridgeConfig(response_grace=0, **config))
    sent: list[dict] = []
    client._connected = True
    client._writer = MagicMock()
    client._writer.write = MagicMock(side_effect=lambda raw: sent.append(json.loads(raw)))
    client._writer.drain = AsyncMock()
    client._lock = asyncio.Lock()
    return client, sent


@pytest.mark.asyncio
async def test_request_carries_resolved_timeout():
    client, sent = _fake_connected_client(request_timeout=0.05)
    with pytest.raises(TimeoutError_) as exc_info:
        await client.send_command("get_scene_info", {"timeout": 0.02})
    assert sent[0]["timeout"] == 0.02
    assert "No reply from Blender for 'get_scene_info'" in exc_info.value.message
    assert exc_info.value.details["timeout"] == 0.02


@pytest.mark.asyncio
async def test_addon_timeout_reply_is_passed_through():
    client, sent = _fake_connected_client(request_timeout=5)

    async def reply_soon():
        while not sent:
            await asyncio.sleep(0.001)
        await client._handle_incoming(
            {
                "type": "response",
                "id": sent[0]["id"],
                "success": False,
                "error_code": "TIMEOUT",
                "error": "'x' did not start within 5s",
                "details": {"started": False},
            }
        )

    task = asyncio.create_task(reply_soon())
    with pytest.raises(BlenderMCPError) as exc_info:
        await client.send_command("x", {})
    await task
    assert exc_info.value.code == ErrorCode.TIMEOUT
    assert "did not start" in exc_info.value.message
    assert exc_info.value.details == {"started": False}


# --- addon execution queue ----------------------------------------------------------


def test_job_runs_and_returns_result():
    job = eq.submit(lambda: 42)
    eq._timer()
    assert eq.wait(job, 1) == 42


def test_job_cancelled_when_it_times_out_before_starting():
    ran = []
    job = eq.submit(lambda: ran.append(1))
    with pytest.raises(eq.JobNotStartedError):
        eq.wait(job, 0.01)
    eq._timer()  # main thread gets to it later
    assert ran == []
    assert job.state == eq.CANCELLED


def test_job_reported_still_running_when_it_times_out_after_starting():
    release = threading.Event()
    job = eq.submit(lambda: release.wait(2))
    worker = threading.Thread(target=eq._timer)
    worker.start()
    while job.state == eq.QUEUED:
        pass
    with pytest.raises(eq.JobStillRunningError):
        eq.wait(job, 0.01)
    release.set()
    worker.join()
    assert job.state == eq.DONE


def test_job_skipped_when_should_run_is_false():
    ran = []
    job = eq.submit(lambda: ran.append(1), should_run=lambda: False)
    eq._timer()
    with pytest.raises(eq.JobSkippedError):
        eq.wait(job, 1)
    assert ran == []


def test_job_error_is_raised():
    def boom():
        raise ValueError("bad")

    job = eq.submit(boom)
    eq._timer()
    with pytest.raises(RuntimeError, match="bad"):
        eq.wait(job, 1)


# --- addon bridge server ------------------------------------------------------------


def test_client_gone_detects_closed_peer():
    a, b = socket.socketpair()
    try:
        assert bridge.client_gone(a) is False
        b.sendall(b"next request\n")
        assert bridge.client_gone(a) is False  # pending data: still connected
        a.recv(100)
        b.close()
        assert bridge.client_gone(a) is True
    finally:
        a.close()


def test_client_gone_none_is_connected():
    assert bridge.client_gone(None) is False


def test_request_timeout_from_message_or_prefs():
    prefs = types.SimpleNamespace(execution_timeout=45.0)
    assert bridge.request_timeout({}, prefs) == 45.0
    assert bridge.request_timeout({"timeout": 300}, prefs) == 300.0
    assert bridge.request_timeout({"timeout": "junk"}, prefs) == 45.0
    assert bridge.request_timeout({"timeout": 0.1}, prefs) == bridge.MIN_TIMEOUT
    assert bridge.request_timeout({"timeout": 10**9}, prefs) == bridge.MAX_TIMEOUT
    assert bridge.request_timeout({}, None) == 60.0


@pytest.mark.parametrize(
    ("exc", "started", "phrase"),
    [
        (eq.JobNotStartedError("x"), False, "cancelled and nothing changed"),
        (eq.JobStillRunningError("x"), True, "still running in Blender"),
    ],
)
def test_dispatch_returns_clear_timeout_response(monkeypatch, exc, started, phrase):
    def fake_run(func, timeout, should_run=None):
        raise exc

    monkeypatch.setattr(bridge.execution_queue, "run_on_main_thread", fake_run)
    monkeypatch.setattr(bridge, "_prefs", lambda: None)
    handlers = types.ModuleType("blender_addon.handlers")
    handlers.dispatch = lambda c, p: None
    monkeypatch.setitem(sys.modules, "blender_addon.handlers", handlers)

    resp = bridge._dispatch_request({"id": "r1", "command": "render_scene", "timeout": 120})
    assert resp["success"] is False
    assert resp["error_code"] == "TIMEOUT"
    assert resp["id"] == "r1"
    assert resp["details"] == {"command": "render_scene", "timeout": 120.0, "started": started}
    assert phrase in resp["error"]


def test_dispatch_passes_client_check_to_queue(monkeypatch):
    seen = {}

    def fake_run(func, timeout, should_run=None):
        seen["should_run"] = should_run()
        seen["timeout"] = timeout
        return {"success": True, "result": "ok"}, {}

    monkeypatch.setattr(bridge.execution_queue, "run_on_main_thread", fake_run)
    monkeypatch.setattr(bridge, "_prefs", lambda: None)
    monkeypatch.setattr(bridge, "client_gone", lambda c: True)
    handlers = types.ModuleType("blender_addon.handlers")
    handlers.dispatch = lambda c, p: None
    monkeypatch.setitem(sys.modules, "blender_addon.handlers", handlers)

    message = {"id": "r2", "command": "get_scene_info", "timeout": 7}
    bridge._dispatch_request(message, client=object())
    assert seen == {"should_run": False, "timeout": 7.0}
