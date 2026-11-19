import pytest

from blender_mcp.config import Settings
from blender_mcp.exceptions import PathDeniedError, PermissionDeniedError
from blender_mcp.security.permissions import require_confirmation, require_tool_group
from blender_mcp.security.script_policy import ScriptPolicy
from blender_mcp.security.validation import validate_path


def test_path_allowlist(tmp_path):
    allowed = tmp_path / "ok"
    allowed.mkdir()
    target = allowed / "file.txt"
    target.write_text("x", encoding="utf-8")
    resolved = validate_path(str(target), allowed_directories=[str(allowed)], must_exist=True)
    assert resolved.exists()

    outside = tmp_path / "nope" / "file.txt"
    outside.parent.mkdir()
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(PathDeniedError):
        validate_path(str(outside), allowed_directories=[str(allowed)])


def test_tool_group_disabled():
    settings = Settings()
    settings.tool_groups.scene = False
    with pytest.raises(PermissionDeniedError):
        require_tool_group(settings, "scene")


def test_script_policy_restricted():
    settings = Settings(script_permission="restricted", safe_execution_mode=True)
    policy = ScriptPolicy(settings)
    with pytest.raises(PermissionDeniedError):
        policy.assert_can_execute()


def test_script_policy_confirmation():
    settings = Settings(script_permission="confirmation", safe_execution_mode=False)
    policy = ScriptPolicy(settings)
    with pytest.raises(PermissionDeniedError):
        policy.assert_can_execute(confirmed=False)
    policy.assert_can_execute(confirmed=True)


def test_destructive_confirmation():
    settings = Settings(confirm_destructive=True)
    with pytest.raises(PermissionDeniedError):
        require_confirmation(settings, confirmed=False, action="delete_object")
