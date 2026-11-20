"""Bridge tests over real TCP sockets.

Two kinds of peer:
- the addon's own connection handler (``bridge_server._handle_client``) with bpy
  replaced by a fake command table, so server client and addon talk for real;
- small hand-written servers, for behaviour the addon never produces (replies out
  of order, connection dropped mid-request).
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import json
import socket
import sys
import threading
import time
import types
from pathlib import Path

import pytest

from blender_mcp.config import BridgeConfig
from blender_mcp.exceptions import BlenderMCPError, BlenderNotConnectedError, ErrorCode
from blender_mcp.protocol.client import BlenderBridgeClient

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


bridge = _load_addon_module("bridge_server")

UNICODE = "héllo wörld · 日本語 · emoji 🎨🧊 · Ελληνικά · עברית"


def _commands() -> dict:
    def echo(params):
        return {"echo": params}

    def big(params):
        return {"data": "x" * int(params["size"])}

    def slow(params):
        time.sleep(float(params.get("seconds", 0.2)))
        return {"slept": params.get("seconds", 0.2), "tag": params.get("tag")}

    def fail(params):
        return {"success": False, "error_code": "OBJECT_NOT_FOUND", "error": "Object not found: X"}

    return {"echo": echo, "big": big, "slow": slow, "fail": fail}


@pytest.fixture
def addon_port(monkeypatch):
    """Run the addon's accept loop + per-client handler on a free port, no Blender."""
    commands = _commands()

    def dispatch(command, params):
        handler = commands.get(command)
        if handler is None:
            return {"success": False, "error_code": "NOT_IMPLEMENTED", "error": command}
        result = handler(params)
        return (
            result
            if isinstance(result, dict) and "success" in result
            else {"success": True, "result": result}
        )

    handlers = types.ModuleType("blender_addon.handlers")
    handlers.dispatch = dispatch
    monkeypatch.setitem(sys.modules, "blender_addon.handlers", handlers)
    # Blender's main thread, approximated: one lock so commands never overlap.
    main_thread = threading.Lock()

    def run_on_main_thread(func, timeout=60.0, should_run=None):
        with main_thread:
            if should_run is not None and not should_run():
                raise bridge.execution_queue.JobSkippedError("skipped")
            return func()

    monkeypatch.setattr(bridge.execution_queue, "run_on_main_thread", run_on_main_thread)
    monkeypatch.setattr(bridge, "_prefs", lambda: None)
    monkeypatch.setattr(
        bridge, "_authenticate", lambda token: (token in ("", "secret"), {"addon_version": "test"})
    )
    monkeypatch.setattr(bridge, "log", lambda message: None)
    bridge._stop_event.clear()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(8)
    server.settimeout(0.2)
    port = server.getsockname()[1]
    stop = threading.Event()

    def accept_loop():
        while not stop.is_set():
            try:
                client, addr = server.accept()
            except (TimeoutError, OSError):
                continue
            threading.Thread(target=bridge._handle_client, args=(client, addr), daemon=True).start()

    thread = threading.Thread(target=accept_loop, daemon=True)
    thread.start()
    yield port
    stop.set()
    thread.join(timeout=2)
    server.close()


def _client(port: int, **kw) -> BlenderBridgeClient:
    return BlenderBridgeClient(
        BridgeConfig(
            host="127.0.0.1",
            port=port,
            connection_timeout=2,
            request_timeout=10,
            heartbeat_interval=60,
            **kw,
        )
    )


def _raw_connect(port: int, token: str = "") -> socket.socket:
    sock = socket.create_connection(("127.0.0.1", port), timeout=5)
    sock.sendall((json.dumps({"type": "auth", "token": token}) + "\n").encode())
    assert json.loads(_readline(sock))["success"] is True
    return sock


def _readline(sock: socket.socket) -> bytes:
    data = b""
    while not data.endswith(b"\n"):
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
    return data


# --- against the real addon handler -------------------------------------------------


async def test_round_trip(addon_port):
    client = _client(addon_port)
    await client.connect()
    try:
        r = await client.send_command("echo", {"a": 1, "nested": {"b": [1, 2, 3]}})
        assert r["success"] is True
        assert r["result"] == {"echo": {"a": 1, "nested": {"b": [1, 2, 3]}}}
        assert client.addon_info == {"addon_version": "test"}
    finally:
        await client.disconnect()


@pytest.mark.parametrize("size", [70 * 1024, 1024 * 1024, 8 * 1024 * 1024])
async def test_large_response_payloads(addon_port, size):
    """Above asyncio's 64 KiB default line limit and well into screenshot sizes."""
    client = _client(addon_port)
    await client.connect()
    try:
        r = await client.send_command("big", {"size": size})
        assert len(r["result"]["data"]) == size
        # The connection is still in sync afterwards.
        assert (await client.send_command("echo", {"after": True}))["result"]["echo"] == {
            "after": True
        }
    finally:
        await client.disconnect()


async def test_large_request_payload(addon_port):
    client = _client(addon_port)
    await client.connect()
    try:
        code = "#" * (900 * 1024)  # close to the addon's 1 MiB request limit
        r = await client.send_command("echo", {"code": code})
        assert len(r["result"]["echo"]["code"]) == len(code)
    finally:
        await client.disconnect()


async def test_unicode_round_trip(addon_port):
    client = _client(addon_port)
    await client.connect()
    try:
        r = await client.send_command("echo", {"name": UNICODE})
        assert r["result"]["echo"]["name"] == UNICODE
    finally:
        await client.disconnect()


def test_request_split_byte_by_byte_including_multibyte_chars(addon_port):
    """Every byte in its own TCP send, so multi-byte UTF-8 characters arrive split."""
    sock = _raw_connect(addon_port)
    try:
        request = {"type": "request", "id": "split", "command": "echo", "params": {"name": UNICODE}}
        raw = (json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8")
        assert len(raw) > len(raw.decode("utf-8"))  # really contains multi-byte chars
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        for i in range(len(raw)):
            sock.sendall(raw[i : i + 1])
        reply = json.loads(_readline(sock).decode("utf-8"))
        assert reply["id"] == "split"
        assert reply["result"]["echo"]["name"] == UNICODE
    finally:
        sock.close()


def test_two_requests_in_one_send_both_answered_in_order(addon_port):
    sock = _raw_connect(addon_port)
    try:
        lines = b"".join(
            (
                json.dumps(
                    {"type": "request", "id": f"r{i}", "command": "echo", "params": {"i": i}}
                )
                + "\n"
            ).encode()
            for i in range(2)
        )
        sock.sendall(lines)
        buf = b""
        while buf.count(b"\n") < 2:
            buf += sock.recv(65536)
        ids = [json.loads(line)["id"] for line in buf.splitlines()]
        assert ids == ["r0", "r1"]
    finally:
        sock.close()


def test_invalid_json_line_does_not_kill_connection(addon_port):
    sock = _raw_connect(addon_port)
    try:
        sock.sendall(b"{not json}\n")
        assert json.loads(_readline(sock))["error"] == "Invalid JSON"
        sock.sendall(
            (
                json.dumps({"type": "request", "id": "ok", "command": "echo", "params": {}}) + "\n"
            ).encode()
        )
        assert json.loads(_readline(sock))["id"] == "ok"
    finally:
        sock.close()


def test_oversized_request_rejected(addon_port):
    sock = _raw_connect(addon_port)
    try:
        payload = b"a" * (bridge.MAX_REQUEST_BYTES + 10)  # no newline: one huge line
        with contextlib.suppress(OSError):  # the addon may close before we finish sending
            sock.sendall(payload)
        reply = json.loads(_readline(sock))
        assert reply["error"] == "Request too large"
    finally:
        sock.close()


def test_request_before_auth_rejected(addon_port):
    sock = socket.create_connection(("127.0.0.1", addon_port), timeout=5)
    try:
        sock.sendall(b'{"type": "request", "id": "x", "command": "echo"}\n')
        reply = json.loads(_readline(sock))
        assert reply["error_code"] == "AUTH_FAILED"
        assert sock.recv(10) == b""  # and the connection is closed
    finally:
        sock.close()


async def test_concurrent_requests_one_client_all_matched(addon_port):
    """Many in flight at once on one connection; every reply reaches its own caller."""
    client = _client(addon_port)
    await client.connect()
    try:
        results = await asyncio.gather(
            *(client.send_command("echo", {"i": i, "s": UNICODE * (i % 3)}) for i in range(40))
        )
        for i, r in enumerate(results):
            assert r["result"]["echo"] == {"i": i, "s": UNICODE * (i % 3)}
    finally:
        await client.disconnect()


async def test_concurrent_clients(addon_port):
    clients = [_client(addon_port) for _ in range(4)]
    await asyncio.gather(*(c.connect() for c in clients))
    try:
        results = await asyncio.gather(
            *(c.send_command("slow", {"seconds": 0.05, "tag": n}) for n, c in enumerate(clients))
        )
        assert [r["result"]["tag"] for r in results] == [0, 1, 2, 3]
    finally:
        await asyncio.gather(*(c.disconnect() for c in clients))


async def test_addon_error_becomes_typed_exception(addon_port):
    client = _client(addon_port)
    await client.connect()
    try:
        with pytest.raises(BlenderMCPError) as exc_info:
            await client.send_command("fail", {})
        assert exc_info.value.code == ErrorCode.OBJECT_NOT_FOUND
        # Still usable afterwards.
        assert (await client.send_command("echo", {}))["success"] is True
    finally:
        await client.disconnect()


async def test_auth_token_rejected(addon_port):
    client = _client(addon_port, auth_token="wrong")
    with pytest.raises(BlenderMCPError) as exc_info:
        await client.connect()
    assert exc_info.value.code == ErrorCode.AUTH_FAILED


# --- against hand-written peers -----------------------------------------------------


async def _fake_addon(handle_requests):
    """Start an NDJSON peer that accepts auth, then hands requests to a coroutine."""

    async def handle(reader, writer):
        await reader.readline()  # auth
        writer.write(b'{"type": "response", "id": "", "success": true, "result": {}}\n')
        await writer.drain()
        await handle_requests(reader, writer)

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def test_out_of_order_replies_matched_by_id():
    async def reverse(reader, writer):
        reqs = [json.loads(await reader.readline()) for _ in range(5)]
        for req in reversed(reqs):
            reply = {"type": "response", "id": req["id"], "success": True, "result": req["params"]}
            writer.write((json.dumps(reply) + "\n").encode())
        await writer.drain()
        await asyncio.sleep(1)

    server, port = await _fake_addon(reverse)
    client = _client(port)
    try:
        await client.connect()
        results = await asyncio.gather(*(client.send_command("x", {"n": n}) for n in range(5)))
        assert [r["result"]["n"] for r in results] == [0, 1, 2, 3, 4]
    finally:
        await client.disconnect()
        server.close()
        await server.wait_closed()


async def test_reply_split_across_writes_with_multibyte_char():
    async def dribble(reader, writer):
        req = json.loads(await reader.readline())
        reply = {"type": "response", "id": req["id"], "success": True, "result": UNICODE}
        raw = (json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8")
        for i in range(0, len(raw), 3):  # 3-byte pieces split the 4-byte emoji
            writer.write(raw[i : i + 3])
            await writer.drain()
            await asyncio.sleep(0)
        await asyncio.sleep(1)

    server, port = await _fake_addon(dribble)
    client = _client(port)
    try:
        await client.connect()
        assert (await client.send_command("x", {}))["result"] == UNICODE
    finally:
        await client.disconnect()
        server.close()
        await server.wait_closed()


async def test_connection_drop_fails_pending_requests_promptly():
    async def drop(reader, writer):
        await reader.readline()
        writer.close()

    server, port = await _fake_addon(drop)
    client = _client(port)
    try:
        await client.connect()
        start = time.monotonic()
        with pytest.raises(BlenderNotConnectedError):
            await client.send_command("x", {})
        assert time.monotonic() - start < 3  # not the 10s request timeout
    finally:
        await client.disconnect()
        server.close()
        await server.wait_closed()


async def test_unknown_reply_ids_and_garbage_lines_ignored():
    async def noisy(reader, writer):
        req = json.loads(await reader.readline())
        writer.write(b"not json at all\n")
        writer.write(b'{"type": "response", "id": "stranger", "success": true}\n')
        writer.write(b'{"type": "status", "busy": true}\n')
        reply = {"type": "response", "id": req["id"], "success": True, "result": "mine"}
        writer.write((json.dumps(reply) + "\n").encode())
        await writer.drain()
        await asyncio.sleep(1)

    server, port = await _fake_addon(noisy)
    client = _client(port)
    try:
        await client.connect()
        assert (await client.send_command("x", {}))["result"] == "mine"
        assert client.addon_info.get("busy") is True
    finally:
        await client.disconnect()
        server.close()
        await server.wait_closed()
