"""TCP bridge server hosted inside Blender."""

from __future__ import annotations

import json
import select
import socket
import threading
import time
import traceback
from typing import Any

from . import execution_queue

DEFAULT_PORT = 9877
MAX_REQUEST_BYTES = 1_048_576
MIN_TIMEOUT = 1.0
MAX_TIMEOUT = 3600.0

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


def is_server_alive() -> bool:
    """True only when the accept loop thread is still alive and marked running."""
    return bool(_state.get("running")) and _server_thread is not None and _server_thread.is_alive()


def probe_listen(timeout: float = 0.5) -> dict[str, Any]:
    """Attempt a real TCP connect to the configured bridge bind address/port."""
    host = str(_state.get("host") or "127.0.0.1")
    # Clients always connect to loopback when the addon binds 0.0.0.0.
    connect_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    port = int(_state.get("port") or DEFAULT_PORT)
    if not is_server_alive():
        return {
            "ok": False,
            "host": connect_host,
            "port": port,
            "error": "Bridge server is not running",
        }
    try:
        with socket.create_connection((connect_host, port), timeout=timeout):
            return {"ok": True, "host": connect_host, "port": port, "error": ""}
    except OSError as exc:
        return {"ok": False, "host": connect_host, "port": port, "error": str(exc)}


def log(message: str) -> None:
    entry = f"{time.strftime('%H:%M:%S')} {message}"
    logs = _state.setdefault("logs", [])
    logs.append(entry)
    if len(logs) > 200:
        del logs[:-200]


def _prefs():
    from .utils.prefs import get_preferences

    return get_preferences()


def _mark_stopped(reason: str = "") -> None:
    global _server_socket, _server_thread
    _state["running"] = False
    _state["clients"] = 0
    if reason:
        _state["last_error"] = reason
        log(reason)
    if _server_socket is not None:
        try:
            _server_socket.close()
        except OSError:
            pass
    _server_socket = None
    _server_thread = None


def _ensure_handlers_registered() -> None:
    try:
        from .handlers import _REGISTRY, register as register_handlers

        if not _REGISTRY:
            register_handlers()
        log(f"Bridge commands available: {len(_REGISTRY)}")
    except Exception as exc:  # noqa: BLE001
        log(f"Handler registration warning: {exc}")


def start_server() -> dict[str, Any]:
    global _server_socket, _server_thread
    _ensure_handlers_registered()
    if is_server_alive():
        return {"success": True, "result": {"message": "Server already running", **get_state()}}

    # Recover from a stale RUNNING flag left after the accept loop died.
    if _state.get("running") or _server_socket is not None or _server_thread is not None:
        log("Recovering stale bridge state before restart")
        stop_server()

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
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        # Windows: SO_REUSEADDR lets a second process bind the *same* port, so two
        # Blender MCP addons (e.g. this one and "MCP for Blender") would both appear
        # RUNNING while connections go to whichever one Windows picks.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        sock.listen(5)
        sock.settimeout(1.0)
    except OSError as exc:
        sock.close()
        msg = (
            f"Port {port} on {host} is already in use ({exc}). Another Blender instance or "
            "MCP addon (e.g. 'MCP for Blender') is listening there. Stop it or change the "
            "port in the addon preferences and BLENDER_MCP_PORT."
        )
        _state["last_error"] = msg
        log(msg)
        raise OSError(msg) from exc

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
    exit_reason = ""
    try:
        while not _stop_event.is_set():
            try:
                client, addr = _server_socket.accept()
            except socket.timeout:
                continue
            except OSError as exc:
                if not _stop_event.is_set():
                    exit_reason = f"Accept loop stopped: {exc}"
                break
            log(f"Client connected from {addr}")
            threading.Thread(
                target=_handle_client, args=(client, addr), name=f"BlenderMCPClient-{addr}", daemon=True
            ).start()
    finally:
        # Always clear RUNNING so Start / Connection Test reflect reality.
        if _state.get("running") and not _stop_event.is_set():
            _mark_stopped(exit_reason or "Accept loop exited unexpectedly")
        elif _state.get("running"):
            _state["running"] = False


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
                    response = _dispatch_request(message, client)
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


def client_gone(client: socket.socket | None) -> bool:
    """True when the peer has closed ``client``. Never blocks.

    Safe to call while the client's handler thread is waiting on a job: that thread
    is not reading, so readable data is either the next request (still connected)
    or EOF (gone).
    """
    if client is None:
        return False
    try:
        readable, _, _ = select.select([client], [], [], 0)
        if not readable:
            return False
        return client.recv(1, socket.MSG_PEEK) == b""
    except (BlockingIOError, InterruptedError, TimeoutError):
        return False
    except (OSError, ValueError):
        return True


def request_timeout(message: dict[str, Any], prefs: Any) -> float:
    """The request's own ``timeout`` if valid, else the addon preference."""
    default = float(getattr(prefs, "execution_timeout", 60.0) if prefs else 60.0)
    value = message.get("timeout")
    try:
        seconds = float(value) if value is not None else default
    except (TypeError, ValueError):
        seconds = default
    if seconds != seconds or seconds <= 0:  # NaN or non-positive
        seconds = default
    return max(MIN_TIMEOUT, min(seconds, MAX_TIMEOUT))


def _timeout_response(
    request_id: str, command: str, seconds: float, started: bool, duration_ms: float
) -> dict[str, Any]:
    if started:
        error = (
            f"'{command}' is still running in Blender after {seconds:g}s. It can't be "
            "interrupted from here and will finish on its own. Check the scene "
            "(get_scene_info or look) before retrying, or the work may happen twice. "
            "For long jobs pass a larger timeout or split the work into smaller steps."
        )
    else:
        error = (
            f"'{command}' did not start within {seconds:g}s because Blender was busy with "
            "earlier work, so it was cancelled and nothing changed. Retry once Blender "
            "is free."
        )
    return {
        "type": "response",
        "id": request_id,
        "success": False,
        "error_code": "TIMEOUT",
        "error": error,
        "details": {"command": command, "timeout": seconds, "started": started},
        "duration_ms": duration_ms,
    }


def _tracker_call(name: str, default: Any) -> Any:
    """Run an edit_tracker function; tracking problems never fail a command."""
    try:
        from . import edit_tracker

        return getattr(edit_tracker, name)()
    except Exception as exc:  # noqa: BLE001
        log(f"Edit tracking {name} failed: {exc}")
        return default


def _dispatch_request(
    message: dict[str, Any], client: socket.socket | None = None
) -> dict[str, Any]:
    from .handlers import dispatch

    request_id = str(message.get("id", ""))
    command = str(message.get("command", ""))
    params = message.get("params") or {}
    _state["last_request"] = command
    _state["current_operation"] = command
    started = time.time()

    prefs = _prefs()
    tracking = bool(getattr(prefs, "track_user_edits", True)) if prefs else True

    def job():
        # Runs on the main thread: compare with the scene as the last command left it,
        # run this command, then remember the scene as this command left it.
        edits = _tracker_call("collect", {}) if tracking else {}
        try:
            return dispatch(command, params), edits
        finally:
            if tracking:
                _tracker_call("rebaseline", None)

    timeout = request_timeout(message, prefs)
    try:
        result, edits = execution_queue.run_on_main_thread(
            job, timeout=timeout, should_run=lambda: not client_gone(client)
        )
        duration_ms = (time.time() - started) * 1000.0
        _state["last_duration_ms"] = duration_ms
        _state["current_operation"] = ""
        if isinstance(result, dict) and "success" in result:
            payload = {"type": "response", "id": request_id, "duration_ms": duration_ms}
            payload.update(result)
        else:
            payload = {
                "type": "response",
                "id": request_id,
                "success": True,
                "result": result,
                "duration_ms": duration_ms,
            }
        if edits:
            payload["user_edits"] = edits
        return payload
    except (execution_queue.JobNotStartedError, execution_queue.JobStillRunningError) as exc:
        duration_ms = (time.time() - started) * 1000.0
        is_started = isinstance(exc, execution_queue.JobStillRunningError)
        # A job still running keeps the operation label until it finishes.
        if not is_started:
            _state["current_operation"] = ""
        _state["last_duration_ms"] = duration_ms
        _state["last_error"] = f"{command} timed out after {timeout:g}s"
        log(_state["last_error"] + (" (still running)" if is_started else " (cancelled)"))
        return _timeout_response(request_id, command, timeout, is_started, duration_ms)
    except execution_queue.JobSkippedError:
        _state["current_operation"] = ""
        log(f"Skipped {command}: client disconnected")
        return {
            "type": "response",
            "id": request_id,
            "success": False,
            "error_code": "CONNECTION_ERROR",
            "error": f"'{command}' was skipped because the client disconnected before it ran.",
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
