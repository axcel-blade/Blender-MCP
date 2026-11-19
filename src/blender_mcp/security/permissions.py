"""Tool-group and destructive-operation permission checks."""

from __future__ import annotations

from blender_mcp.config import Settings, ToolGroupsConfig
from blender_mcp.exceptions import PermissionDeniedError


def require_tool_group(settings: Settings, group: str) -> None:
    groups: ToolGroupsConfig = settings.tool_groups
    enabled = getattr(groups, group, None)
    if enabled is False:
        raise PermissionDeniedError(
            f"Tool group '{group}' is disabled in configuration",
            details={"tool_group": group},
        )


def require_confirmation(settings: Settings, *, confirmed: bool, action: str) -> None:
    if settings.confirm_destructive and not confirmed:
        raise PermissionDeniedError(
            f"Destructive action '{action}' requires confirmed=true",
            details={"action": action},
        )
