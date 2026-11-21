from pathlib import Path

from blender_mcp.tools import app


def test_find_blender_uses_configured_path(tmp_path: Path) -> None:
    exe = tmp_path / "blender.exe"
    exe.write_text("")
    assert app.find_blender(str(exe)) == str(exe)


def test_find_blender_missing_configured_path(tmp_path: Path) -> None:
    assert app.find_blender(str(tmp_path / "nope.exe")) is None


def test_blend_file_tool_registered_in_core() -> None:
    from blender_mcp.tools.registry import CORE_TOOLS

    assert {"blend_file", "open_blender", "close_blender"} <= CORE_TOOLS
