"""Script execution permission policy."""

from __future__ import annotations

from blender_mcp.config import ScriptPermission, Settings
from blender_mcp.exceptions import PermissionDeniedError


class ScriptPolicy:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def mode(self) -> ScriptPermission:
        return self.settings.script_permission

    def assert_can_execute(self, *, preview_only: bool = False, confirmed: bool = False) -> None:
        if self.settings.safe_execution_mode and self.mode == ScriptPermission.RESTRICTED:
            raise PermissionDeniedError(
                "Arbitrary script execution is disabled (script_permission=restricted). "
                "Use dedicated MCP tools, or set script_permission to confirmation/trusted.",
            )

        if preview_only:
            return

        if self.mode == ScriptPermission.CONFIRMATION and not confirmed:
            raise PermissionDeniedError(
                "Script execution requires confirmed=true in confirmation mode. "
                "Preview the script first, then re-run with confirmed=true.",
            )

        if self.mode == ScriptPermission.RESTRICTED:
            raise PermissionDeniedError("Script execution is restricted")

    def warning_text(self) -> str:
        return (
            "execute_blender_code runs arbitrary Python inside Blender with access to files, "
            "network, and system capabilities available to the Blender process. "
            "This is not a secure sandbox. Save your work and only enable trusted/confirmation "
            "modes when you understand the risk."
        )
