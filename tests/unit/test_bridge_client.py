import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blender_mcp.config import BridgeConfig
from blender_mcp.exceptions import BlenderNotConnectedError, TimeoutError_
from blender_mcp.protocol.client import DEFAULT_READER_LIMIT, BlenderBridgeClient


@pytest.mark.asyncio
async def test_connect_failure():
    client = BlenderBridgeClient(BridgeConfig(host="127.0.0.1", port=1, connection_timeout=0.2))
    with pytest.raises(BlenderNotConnectedError) as exc_info:
        await client.connect()
    assert "Open Blender" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_command_timeout():
    client = BlenderBridgeClient(BridgeConfig(request_timeout=0.05))
    client._connected = True
    client._writer = MagicMock()
    client._writer.write = MagicMock()
    client._writer.drain = AsyncMock()
    client._lock = asyncio.Lock()

    with pytest.raises(TimeoutError_):
        await client.send_command("get_scene_info", {})


@pytest.mark.asyncio
async def test_connect_authenticates_before_read_loop():
    client = BlenderBridgeClient(BridgeConfig(host="127.0.0.1", port=9877, connection_timeout=1.0))
    order: list[str] = []
    open_kwargs: dict = {}

    async def fake_open_connection(host, port, **kwargs):
        open_kwargs.update(kwargs)
        reader = AsyncMock()
        writer = MagicMock()
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return reader, writer

    async def fake_authenticate():
        order.append("auth")

    def fake_create_task(coro, name=None):
        order.append(name or "task")
        # Close the coroutine to avoid "never awaited" warnings.
        coro.close()
        task = MagicMock()
        task.cancel = MagicMock()
        return task

    open_conn = patch(
        "blender_mcp.protocol.client.asyncio.open_connection",
        side_effect=fake_open_connection,
    )
    create_task = patch(
        "blender_mcp.protocol.client.asyncio.create_task",
        side_effect=fake_create_task,
    )
    authenticate = patch.object(client, "_authenticate", side_effect=fake_authenticate)
    with open_conn, create_task, authenticate:
        await client.connect()

    assert order[0] == "auth"
    assert "blender-bridge-reader" in order
    assert order.index("auth") < order.index("blender-bridge-reader")
    assert open_kwargs.get("limit") == DEFAULT_READER_LIMIT


@pytest.mark.asyncio
async def test_read_loop_accepts_large_ndjson_payload():
    """Regression: screenshot base64 lines exceed asyncio's default 64 KiB limit."""
    client = BlenderBridgeClient(
        BridgeConfig(host="127.0.0.1", port=9877, connection_timeout=1.0),
        reader_limit=DEFAULT_READER_LIMIT,
    )
    large_b64 = "A" * (100 * 1024)
    response_line = (
        '{"type":"response","id":"req-1","success":true,'
        f'"result":{{"image_base64":"{large_b64}"}}}}\n'
    ).encode()

    reader = asyncio.StreamReader(limit=DEFAULT_READER_LIMIT)
    reader.feed_data(response_line)
    reader.feed_eof()
    client._reader = reader
    client._connected = True

    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    client._pending["req-1"] = future

    await client._read_loop()

    assert future.done()
    assert not isinstance(future.exception(), Exception) or future.exception() is None
    response = future.result()
    assert response.success is True
    assert len(response.result["image_base64"]) == len(large_b64)


@pytest.mark.asyncio
async def test_foreign_addon_on_port_gives_clear_error():
    """A non-NDJSON peer (e.g. 'MCP for Blender') must not hang or look like auth failure."""

    async def handle(reader, writer):
        await reader.readline()
        writer.write(b'{"status": "error", "message": "Unknown command type: auth"}')
        await writer.drain()
        await asyncio.sleep(2)
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        client = BlenderBridgeClient(
            BridgeConfig(host="127.0.0.1", port=port, connection_timeout=0.5)
        )
        with pytest.raises(BlenderNotConnectedError) as exc_info:
            await client.connect()
        assert "not the Blender MCP addon" in str(exc_info.value)
    finally:
        server.close()
        await server.wait_closed()
