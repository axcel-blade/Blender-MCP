"""One tool for managing the open .blend file: save, rename, open, new, list."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.security.validation import validate_path
from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.utils.results import fail_from_exception

Action = Literal[
    "info",
    "save",
    "save_as",
    "save_copy",
    "rename",
    "open",
    "new",
    "revert",
    "list",
    "recent",
    "autosaves",
    "recover",
]

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
        keep_old: bool = False,
    ) -> dict[str, Any]:
        """Manage the open .blend file.

        - ``info``: current path and whether there are unsaved changes
        - ``save``: save in place (``path`` empty) or to ``path``
        - ``save_as`` / ``save_copy``: save to ``path`` (copy keeps working on the current file)
        - ``rename``: rename the file on disk; ``path`` is a new name or full path. The old
          file goes to the system trash (``keep_old`` leaves it in place)
        - ``open`` / ``new``: open ``path`` or start a new file; refuse on unsaved changes
          unless ``discard_changes`` (ask the user first)
        - ``revert``: reload the last saved version, dropping unsaved changes (ask first)
        - ``list``: .blend files in ``path`` (default: the current file's folder)
        - ``recent``: Blender's File > Open Recent list
        - ``autosaves``: autosave files and the last session (``quit.blend``), newest first
        - ``recover``: open the autosave at ``path``, or the last session when ``path`` is
          empty. The last session keeps its original path (``save`` writes over it); an
          autosave points at the temp folder, so keep it with ``save_as``. Refuses on
          unsaved changes unless ``discard_changes``
        """
        if action in _PATH_KEY and not path:
            return {
                "success": False,
                "error_code": "INVALID_PARAMETER",
                "error": f"action={action!r} needs a path",
                "details": {},
            }
        dirs = ctx.settings.allowed_directories
        target = path
        if dirs and action == "rename" and not ("/" in path or "\\" in path):
            # A bare name lands next to the open file: resolve it so the check sees
            # the real destination.
            info = await call_blender(ctx, "blend_file_info", {}, group="import_export")
            if info.get("success") is False:
                return info
            current = (info.get("result") or {}).get("path")
            if current:
                target = str(Path(current).parent / path)
        try:
            # recover only reads autosaves; the addon limits it to Blender's temp folder.
            if target and action != "recover":
                validate_path(target, allowed_directories=dirs, must_exist=action == "open")
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)

        commands: dict[str, tuple[str, dict[str, Any]]] = {
            "info": ("blend_file_info", {}),
            "save": ("save_blend_file", {"path": path or None, "overwrite": True}),
            "save_as": ("save_as", {"path": path, "overwrite": overwrite}),
            "save_copy": ("save_copy", {"path": path, "overwrite": overwrite}),
            "rename": ("rename_blend_file", {"new_name": path, "keep_old": keep_old}),
            "open": (
                "open_blend_file",
                {"path": path, "check_unsaved": True, "discard_changes": discard_changes},
            ),
            "new": ("new_blend_file", {"discard_changes": discard_changes}),
            "revert": ("revert_blend_file", {}),
            "list": ("list_blend_files", {"directory": path, "recursive": recursive}),
            "recent": ("recent_blend_files", {}),
            "autosaves": ("list_autosaves", {}),
            "recover": (
                "recover_blend_file",
                {"path": path or None, "discard_changes": discard_changes},
            ),
        }
        command, params = commands[action]
        return await call_blender(ctx, command, params, group="import_export")
