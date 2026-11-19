"""TCP bridge server hosted inside Blender."""

from __future__ import annotations

import json
import socket
import threading
import time
import traceback
from typing import Any

from . import execution_queue

DEFAULT_PORT = 9876
MAX_REQUEST_BYTES = 1_048_576

_server_socket: socket.socket | None = None
_server_thread: threading.Thread | None = None
_stop_event = threading.Event()
_state: dict[str, Any] = {
    "running": False,
    "host": "127.0.0.1",
    "port": DEFAULT_PORT,
    "clients": 0,
    "last_request": "",
    "current_operation": "",
    "last_error": "",
    "last_duration_ms": 0.0,
    "logs": [],
}


def get_state() -> dict[str, Any]:
    return dict(_state)


def log(message: str) -> None:
    entry = f"{time.strftime('%H:%M:%S')} {message}"
    logs = _state.setdefault("logs", [])
    logs.append(entry)
    if len(logs) > 200:
        del logs[:-200]


def _prefs():
    from .utils.prefs import get_preferences

    return get_preferences()


def start_server() -> dict[str, Any]:
    global _server_socket, _server_thread
    if _state.get("running"):
        return {"success": True, "result": {"message": "Server already running", **get_state()}}

    prefs = _prefs()
    host = "127.0.0.1"
    port = DEFAULT_PORT
    if prefs is not None:
        port = int(prefs.port)
        if prefs.allow_remote:
            host = prefs.bind_address or "0.0.0.0"
        else:
            host = "127.0.0.1"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        sock.listen(5)
        sock.settimeout(1.0)
    except OSError as exc:
        _state["last_error"] = str(exc)
        log(f"Failed to bind {host}:{port}: {exc}")
        raise

    _server_socket = sock
    _stop_event.clear()
    _state.update({"running": True, "host": host, "port": port, "last_error": ""})
    _server_thread = threading.Thread(target=_serve_loop, name="BlenderMCPBridge", daemon=True)
    _server_thread.start()
    log(f"Bridge listening on {host}:{port}")
    return {"success": True, "result": get_state()}


def stop_server() -> dict[str, Any]:
    global _server_socket, _server_thread
    _stop_event.set()
    _state["running"] = False
    if _server_socket is not None:
        try:
            _server_socket.close()
        except OSError:
            pass
    _server_socket = None
    if _server_thread is not None and _server_thread.is_alive():
        _server_thread.join(timeout=2.0)
    _server_thread = None
    _state["clients"] = 0
    log("Bridge stopped")
    return {"success": True, "result": get_state()}


def _serve_loop() -> None:
    assert _server_socket is not None
    while not _stop_event.is_set():
        try:
            client, addr = _server_socket.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        log(f"Client connected from {addr}")
        threading.Thread(
            target=_handle_client, args=(client, addr), name=f"BlenderMCPClient-{addr}", daemon=True
        ).start()


def _handle_client(client: socket.socket, addr: Any) -> None:
    _state["clients"] = int(_state.get("clients", 0)) + 1
    buffer = b""
    authenticated = False
    try:
        client.settimeout(60.0)
        while not _stop_event.is_set():
            chunk = client.recv(65536)
            if not chunk:
                break
            buffer += chunk
            if len(buffer) > MAX_REQUEST_BYTES:
                _send(client, {"type": "response", "id": "", "success": False, "error_code": "INVALID_PARAMETER", "error": "Request too large"})
                break
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    message = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    _send(
                        client,
                        {
                            "type": "response",
                            "id": "",
                            "success": False,
                            "error_code": "INVALID_PARAMETER",
                            "error": "Invalid JSON",
                        },
                    )
                    continue

                msg_type = message.get("type")
                if msg_type == "auth":
                    ok, info = _authenticate(message.get("token", ""))
                    _send(client, {"type": "response", "id": "", "success": ok, "result": info if ok else None, "error": None if ok else "Authentication failed", "error_code": None if ok else "AUTH_FAILED"})
                    authenticated = ok
                    if not ok:
                        return
                    continue

                if not authenticated:
                    _send(client, {"type": "response", "id": message.get("id", ""), "success": False, "error_code": "AUTH_FAILED", "error": "Not authenticated"})
                    return

                if msg_type == "ping":
                    _send(client, {"type": "pong", "id": message.get("id", "")})
                    continue

                if msg_type == "request":
                    response = _dispatch_request(message)
                    _send(client, response)
                    continue
    except Exception as exc:  # noqa: BLE001
        _state["last_error"] = str(exc)
        log(f"Client error {addr}: {exc}")
    finally:
        try:
            client.close()
        except OSError:
            pass
        _state["clients"] = max(0, int(_state.get("clients", 1)) - 1)
        log(f"Client disconnected {addr}")


def _authenticate(token: str) -> tuple[bool, dict[str, Any]]:
    prefs = _prefs()
    expected = getattr(prefs, "auth_token", "") if prefs else ""
    if expected and token != expected:
        return False, {}
    import bpy
    from . import ADDON_VERSION

    return True, {
        "blender_version": bpy.app.version_string,
        "addon_version": ADDON_VERSION,
        "host": _state.get("host"),
        "port": _state.get("port"),
    }


def _dispatch_request(message: dict[str, Any]) -> dict[str, Any]:
    from .handlers import dispatch

    request_id = str(message.get("id", ""))
    command = str(message.get("command", ""))
    params = message.get("params") or {}
    _state["last_request"] = command
    _state["current_operation"] = command
    started = time.time()

    def job():
        return dispatch(command, params)

    try:
        prefs = _prefs()
        timeout = float(getattr(prefs, "execution_timeout", 60.0) if prefs else 60.0)
        result = execution_queue.run_on_main_thread(job, timeout=timeout)
        duration_ms = (time.time() - started) * 1000.0
        _state["last_duration_ms"] = duration_ms
        _state["current_operation"] = ""
        if isinstance(result, dict) and "success" in result:
            payload = {"type": "response", "id": request_id, "duration_ms": duration_ms}
            payload.update(result)
            return payload
        return {
            "type": "response",
            "id": request_id,
            "success": True,
            "result": result,
            "duration_ms": duration_ms,
        }
    except Exception as exc:  # noqa: BLE001
        duration_ms = (time.time() - started) * 1000.0
        _state["last_error"] = str(exc)
        _state["current_operation"] = ""
        _state["last_duration_ms"] = duration_ms
        log(f"Error in {command}: {exc}")
        return {
            "type": "response",
            "id": request_id,
            "success": False,
            "error_code": "OPERATION_FAILED",
            "error": str(exc),
            "details": {"traceback": traceback.format_exc()},
            "duration_ms": duration_ms,
        }


def _send(client: socket.socket, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, ensure_ascii=False, default=str) + "\n").encode("utf-8")
    client.sendall(data)


def register() -> None:
    pass


def unregister() -> None:
    if _state.get("running"):
        stop_server()
