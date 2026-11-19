import pytest

from blender_mcp.config import Settings
from blender_mcp.exceptions import PathDeniedError
from blender_mcp.security.script_policy import ScriptPolicy
from blender_mcp.security.validation import validate_path


def test_path_traversal_blocked(tmp_path):
    allowed = tmp_path / "safe"
    allowed.mkdir()
    evil = tmp_path / "safe" / ".." / "outside.txt"
    # resolve would escape
    (tmp_path / "outside.txt").write_text("x", encoding="utf-8")
    with pytest.raises(PathDeniedError):
        validate_path(str(evil), allowed_directories=[str(allowed)])


def test_trusted_script_mode_allows():
    settings = Settings(script_permission="trusted", safe_execution_mode=False)
    ScriptPolicy(settings).assert_can_execute(confirmed=False)
