"""Async TCP bridge client talking to the Blender addon."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

from blender_mcp.config import BridgeConfig
from blender_mcp.exceptions import (
    AuthFailedError,
    BlenderMCPError,
    BlenderNotConnectedError,
    ErrorCode,
    TimeoutError_,
)
from blender_mcp.protocol.messages import BridgeRequest, BridgeResponse
from blender_mcp.protocol.timeouts import RESPONSE_GRACE, no_reply_message, resolve_timeout

logger = logging.getLogger(__name__)


# Screenshots/render results embed base64 PNG in a single NDJSON line.
# asyncio's default StreamReader limit (64 KiB) truncates those payloads and
# surfaces as "Connection lost" / WinError 10054 on the Blender bridge.
DEFAULT_READER_LIMIT = 32 * 1024 * 1024  # 32 MiB


class BlenderBridgeClient:
    """Newline-delimited JSON client for the Blender addon bridge."""

    def __init__(self, config: BridgeConfig, *, reader_limit: int = DEFAULT_READER_LIMIT) -> None:
        self.config = config
        self._reader_limit = reader_limit
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._pending: dict[str, asyncio.Future[BridgeResponse]] = {}
        self._reader_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._connected = False
        self._last_error: str | None = None
        self._addon_info: dict[str, Any] = {}

    @property
    def connected(self) -> bool:
        return self._connected and self._writer is not None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def addon_info(self) -> dict[str, Any]:
        return dict(self._addon_info)

    async def connect(self) -> None:
        if self.connected:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.config.host,
                    self.config.port,
                    limit=self._reader_limit,
                ),
                timeout=self.config.connection_timeout,
            )
        except (TimeoutError, OSError) as exc:
            self._connected = False
            self._last_error = str(exc)
            raise BlenderNotConnectedError(
                f"Could not connect to Blender at {self.config.host}:{self.config.port}: {exc}. "
                "Open Blender, enable the Blender MCP addon, and confirm the Blender MCP panel "
                "shows RUNNING."
            ) from exc

        self._connected = True
        self._last_error = None
        # Authenticate before starting the shared reader so the auth reply
        # cannot be stolen by `_read_loop` (empty-id responses are not pending).
        await self._authenticate()
        self._reader_task = asyncio.create_task(self._read_loop(), name="blender-bridge-reader")
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(), name="blender-bridge-heartbeat"
        )
        logger.info("Connected to Blender bridge %s:%s", self.config.host, self.config.port)

    async def disconnect(self) -> None:
        self._connected = False
        for task in (self._heartbeat_task, self._reader_task):
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._heartbeat_task = None
        self._reader_task = None

        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        self._writer = None
        self._reader = None

        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(BlenderNotConnectedError("Disconnected from Blender"))
        self._pending.clear()

    async def ensure_connected(self) -> None:
        if self.connected:
            return
        last_exc: Exception | None = None
        for attempt in range(1, self.config.retry_count + 1):
            try:
                await self.connect()
                return
            except BlenderMCPError as exc:
                last_exc = exc
                logger.warning("Connect attempt %s failed: %s", attempt, exc)
                await asyncio.sleep(self.config.retry_delay * attempt)
        if last_exc:
            raise last_exc
        raise BlenderNotConnectedError()

    async def send_command(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        await self.ensure_connected()
        params = params or {}
        timeout = resolve_timeout(
            command,
            params,
            self.config.request_timeout,
            self.config.command_timeouts,
            explicit=timeout,
        )
        request = BridgeRequest(command=command, params=params, timeout=timeout)

        loop = asyncio.get_running_loop()
        future: asyncio.Future[BridgeResponse] = loop.create_future()
        self._pending[request.id] = future

        try:
            await self._write(request.to_dict())
            # The addon enforces `timeout` itself and replies with a precise TIMEOUT
            # (cancelled vs still running); the grace lets that reply arrive first.
            grace = self.config.response_grace
            if grace < 0:
                grace = RESPONSE_GRACE
            response = await asyncio.wait_for(future, timeout=timeout + grace)
        except TimeoutError as exc:
            self._pending.pop(request.id, None)
            self._last_error = f"Timeout waiting for {command}"
            raise TimeoutError_(
                no_reply_message(command, timeout),
                details={"command": command, "request_id": request.id, "timeout": timeout},
            ) from exc
        except BlenderMCPError:
            self._pending.pop(request.id, None)
            raise
        except Exception as exc:  # noqa: BLE001
            self._pending.pop(request.id, None)
            self._last_error = str(exc)
            raise BlenderMCPError(
                f"Bridge communication failed: {exc}",
                code=ErrorCode.CONNECTION_ERROR,
                details={"command": command},
            ) from exc

        result = response.to_tool_result()
        if not response.success:
            code = ErrorCode.OPERATION_FAILED
            if response.error_code:
                try:
                    code = ErrorCode(response.error_code)
                except ValueError:
                    code = ErrorCode.OPERATION_FAILED
            details: dict[str, Any] = dict(response.details or {"command": command})
            if response.user_edits:
                details["user_edits"] = response.user_edits
            raise BlenderMCPError(
                response.error or "Blender operation failed",
                code=code,
                details=details,
            )
        return result

    async def ping(self) -> bool:
        if not self.connected:
            return False
        try:
            await self._write({"type": "ping", "id": BridgeRequest(command="ping").id})
            return True
        except Exception:  # noqa: BLE001
            return False

    async def diagnose(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "mcp_server": "ok",
            "bridge_host": self.config.host,
            "bridge_port": self.config.port,
            "connected": self.connected,
            "last_error": self._last_error,
            "addon_info": self.addon_info,
        }
        try:
            await self.ensure_connected()
            result = await self.send_command("diagnose_blender_connection", {})
            status["connected"] = True
            status["blender"] = result.get("result", result)
        except BlenderMCPError as exc:
            status["connected"] = False
            status["error_code"] = str(exc.code)
            status["error"] = exc.message
        return status

    async def _authenticate(self) -> None:
        await self._write({"type": "auth", "token": self.config.auth_token or ""})
        assert self._reader is not None
        try:
            line = await asyncio.wait_for(
                self._reader.readline(), timeout=self.config.connection_timeout
            )
        except TimeoutError as exc:
            # A non-NDJSON peer (e.g. the "MCP for Blender" addon, which replies
            # without a trailing newline) never completes readline().
            partial = b""
            with contextlib.suppress(Exception):
                partial = await asyncio.wait_for(self._reader.read(4096), timeout=0.2)
            await self.disconnect()
            raise BlenderNotConnectedError(self._foreign_peer_message(partial)) from exc
        except (ValueError, asyncio.LimitOverrunError) as exc:
            await self.disconnect()
            raise BlenderNotConnectedError(self._foreign_peer_message(b"")) from exc

        if not line:
            await self.disconnect()
            raise AuthFailedError("Connection closed during authentication")

        try:
            data = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            await self.disconnect()
            raise BlenderNotConnectedError(self._foreign_peer_message(line)) from exc
        if not isinstance(data, dict) or data.get("type") != "response":
            await self.disconnect()
            raise BlenderNotConnectedError(self._foreign_peer_message(line))
        if not data.get("success", False):
            await self.disconnect()
            raise AuthFailedError(data.get("error") or "Authentication rejected")
        self._addon_info = data.get("result") or {}

    def _foreign_peer_message(self, received: bytes) -> str:
        snippet = received[:120].decode("utf-8", "replace")
        return (
            f"Something is listening on {self.config.host}:{self.config.port} but it is not the "
            "Blender MCP addon (it did not answer the bridge handshake). This usually means "
            "another Blender addon such as 'MCP for Blender' owns the port. Disable it, or set "
            "a different port in the Blender MCP addon preferences and BLENDER_MCP_PORT."
            + (f" Received: {snippet!r}" if snippet else "")
        )

    async def _write(self, payload: dict[str, Any]) -> None:
        if self._writer is None:
            raise BlenderNotConnectedError()
        raw = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        async with self._lock:
            self._writer.write(raw)
            await self._writer.drain()

    async def _read_loop(self) -> None:
        assert self._reader is not None
        try:
            while self._connected:
                line = await self._reader.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from Blender: %r", line[:200])
                    continue
                await self._handle_incoming(data)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            logger.error("Bridge reader error: %s", exc)
        finally:
            self._connected = False
            for fut in list(self._pending.values()):
                if not fut.done():
                    fut.set_exception(BlenderNotConnectedError("Connection lost"))
            self._pending.clear()

    async def _handle_incoming(self, data: dict[str, Any]) -> None:
        msg_type = data.get("type")
        if msg_type == "pong":
            return
        if msg_type == "response":
            response = BridgeResponse.from_dict(data)
            future = self._pending.pop(response.id, None)
            if future and not future.done():
                future.set_result(response)
            return
        if msg_type == "status":
            self._addon_info.update(data)
            return
        logger.debug("Unhandled bridge message type: %s", msg_type)

    async def _heartbeat_loop(self) -> None:
        try:
            while self._connected:
                await asyncio.sleep(self.config.heartbeat_interval)
                if not await self.ping():
                    logger.warning("Heartbeat ping failed")
        except asyncio.CancelledError:
            raise
