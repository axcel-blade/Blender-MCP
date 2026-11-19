"""Bridge protocol between MCP server and Blender addon."""

from blender_mcp.protocol.client import BlenderBridgeClient
from blender_mcp.protocol.messages import BridgeRequest, BridgeResponse

__all__ = ["BlenderBridgeClient", "BridgeRequest", "BridgeResponse"]
