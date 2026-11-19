import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from blender_mcp.config import BridgeConfig
from blender_mcp.exceptions import BlenderNotConnectedError, TimeoutError_
from blender_mcp.protocol.client import BlenderBridgeClient


@pytest.mark.asyncio
async def test_connect_failure():
    client = BlenderBridgeClient(BridgeConfig(host="127.0.0.1", port=1, connection_timeout=0.2))
    with pytest.raises(BlenderNotConnectedError):
        await client.connect()


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
