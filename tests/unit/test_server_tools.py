from blender_mcp.config import load_settings
from blender_mcp.server import create_server


def test_create_server_registers_tools():
    settings = load_settings()
    mcp = create_server(settings)
    # FastMCP keeps tools in _tool_manager
    tools = getattr(mcp, "_tool_manager", None)
    assert tools is not None
    names = set(tools._tools.keys())  # noqa: SLF001
    for required in (
        "get_scene_info",
        "create_cube",
        "create_material",
        "add_modifier",
        "create_camera",
        "create_light",
        "get_viewport_screenshot",
        "diagnose_blender_connection",
        "execute_blender_code",
        "blender_mcp_version",
    ):
        assert required in names, f"missing tool {required}"
