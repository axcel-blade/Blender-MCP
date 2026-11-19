import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blender_mcp.config import BridgeConfig
from blender_mcp.exceptions import BlenderNotConnectedError, TimeoutError_
from blender_mcp.protocol.client import BlenderBridgeClient


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
    client = BlenderBridgeClient(BridgeConfig(host="127.0.0.1", port=9876, connection_timeout=1.0))
    order: list[str] = []

    async def fake_open_connection(host, port):
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
