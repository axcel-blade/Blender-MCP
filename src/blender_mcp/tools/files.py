"""One tool for managing the open .blend file: save, rename, open, new, list."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.security.validation import validate_path
from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.utils.results import fail_from_exception

Action = Literal["info", "save", "save_as", "save_copy", "rename", "open", "new", "revert", "list"]

# Actions that need a path, and the key it is sent under.
_PATH_KEY = {"save_as": "path", "save_copy": "path", "open": "path", "rename": "new_name"}


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool(name="blend_file")
    async def blend_file(
        action: Action = "info",
        path: str = "",
        overwrite: bool = False,
        discard_changes: bool = False,
        recursive: bool = False,
    ) -> dict[str, Any]:
        """Manage the open .blend file.

        - ``info``: current path and whether there are unsaved changes
        - ``save``: save in place (``path`` empty) or to ``path``
        - ``save_as`` / ``save_copy``: save to ``path`` (copy keeps working on the current file)
        - ``rename``: rename the file on disk; ``path`` is a new name or full path
        - ``open`` / ``new``: open ``path`` or start a new file; refuse on unsaved changes
          unless ``discard_changes`` (ask the user first)
        - ``revert``: reload the last saved version, dropping unsaved changes (ask first)
        - ``list``: .blend files in ``path`` (default: the current file's folder)
        """
        if action in _PATH_KEY and not path:
            return {
                "success": False,
                "error_code": "INVALID_PARAMETER",
                "error": f"action={action!r} needs a path",
                "details": {},
            }
        dirs = ctx.settings.allowed_directories
        try:
            if path and ("/" in path or "\\" in path or action != "rename"):
                validate_path(path, allowed_directories=dirs, must_exist=action == "open")
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)

        commands: dict[str, tuple[str, dict[str, Any]]] = {
            "info": ("blend_file_info", {}),
            "save": ("save_blend_file", {"path": path or None, "overwrite": True}),
            "save_as": ("save_as", {"path": path, "overwrite": overwrite}),
            "save_copy": ("save_copy", {"path": path, "overwrite": overwrite}),
            "rename": ("rename_blend_file", {"new_name": path}),
            "open": (
                "open_blend_file",
                {"path": path, "check_unsaved": True, "discard_changes": discard_changes},
            ),
            "new": ("new_blend_file", {"discard_changes": discard_changes}),
            "revert": ("revert_blend_file", {}),
            "list": ("list_blend_files", {"directory": path, "recursive": recursive}),
        }
        command, params = commands[action]
        return await call_blender(ctx, command, params, group="import_export")
