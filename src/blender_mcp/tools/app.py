"""Open and close the Blender application itself."""

from __future__ import annotations

import asyncio
import glob
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.utils.results import ok

# The Blender process this server launched, if any.
_launched: subprocess.Popen[bytes] | None = None


def _candidate_paths() -> list[str]:
    if sys.platform == "win32":
        roots = [os.environ.get("PROGRAMFILES", r"C:\Program Files")]
        if os.environ.get("PROGRAMFILES(X86)"):
            roots.append(os.environ["PROGRAMFILES(X86)"])
        found: list[str] = []
        for root in roots:
            found += glob.glob(os.path.join(root, "Blender Foundation", "Blender*", "blender.exe"))
        found += glob.glob(
            os.path.join(
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                "WindowsApps",
                "BlenderFoundation.Blender*",
                "Blender",
                "blender.exe",
            )
        )
        found += glob.glob(r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe")
        return sorted(found, reverse=True)  # newest version first
    if sys.platform == "darwin":
        apps = glob.glob("/Applications/Blender*.app") + glob.glob(
            str(Path.home() / "Applications" / "Blender*.app")
        )
        return [os.path.join(a, "Contents", "MacOS", "Blender") for a in sorted(apps, reverse=True)]
    return ["/usr/bin/blender", "/snap/bin/blender", "/usr/local/bin/blender"]


def find_blender(configured: str = "") -> str | None:
    """Return the Blender executable: configured path, then PATH, then common installs."""
    if configured:
        return configured if Path(configured).is_file() else None
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    return next((p for p in _candidate_paths() if Path(p).is_file()), None)


async def _bridge_up(ctx: AppContext) -> bool:
    try:
        await ctx.bridge.ensure_connected()
        return ctx.bridge.connected
    except Exception:  # noqa: BLE001
        return False


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool(name="open_blender")
    async def open_blender(file_path: str = "", wait: bool = True) -> dict[str, Any]:
        """Launch Blender when it is not running (no-op if the addon already answers).
        Optionally open ``file_path``. With ``wait`` it returns once the addon bridge
        accepts connections. Set BLENDER_MCP_BLENDER_PATH if Blender is not found."""
        global _launched
        if await _bridge_up(ctx):
            return ok({"already_running": True, "launched": False})

        exe = find_blender(ctx.settings.blender_path)
        if not exe:
            return {
                "success": False,
                "error_code": "BLENDER_NOT_FOUND",
                "error": "Blender executable not found. Set BLENDER_MCP_BLENDER_PATH "
                "to the full path of blender(.exe).",
                "details": {"searched": _candidate_paths()},
            }
        args = [exe]
        if file_path:
            if not Path(file_path).is_file():
                return {
                    "success": False,
                    "error_code": "FILE_NOT_FOUND",
                    "error": f"No such .blend file: {file_path}",
                    "details": {},
                }
            args.append(file_path)

        kwargs: dict[str, Any] = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            kwargs["start_new_session"] = True
        _launched = subprocess.Popen(args, **kwargs)  # noqa: S603

        result = {"launched": True, "pid": _launched.pid, "executable": exe}
        if not wait:
            return ok(result)

        deadline = time.monotonic() + ctx.settings.blender_launch_timeout
        while time.monotonic() < deadline:
            if _launched.poll() is not None:
                return {
                    "success": False,
                    "error_code": "BLENDER_EXITED",
                    "error": f"Blender exited during startup (code {_launched.returncode})",
                    "details": result,
                }
            if await _bridge_up(ctx):
                return ok({**result, "bridge_ready": True})
            await asyncio.sleep(1.0)
        return ok(
            {**result, "bridge_ready": False},
            warning="Blender started but the MCP addon bridge did not answer. Make sure the "
            "addon is installed and enabled with auto-start on.",
        )

    @mcp.tool(name="close_blender")
    async def close_blender(save: bool = False, discard_changes: bool = False) -> dict[str, Any]:
        """Quit Blender. Refuses when there are unsaved changes unless ``save`` (save the
        current file first) or ``discard_changes`` is set. Ask the user before discarding."""
        global _launched
        if await _bridge_up(ctx):
            reply = await call_blender(
                ctx, "quit_blender", {"save": save, "discard_changes": discard_changes}
            )
            if reply.get("success") is False:
                return reply
            await ctx.bridge.disconnect()
            _launched = None
            return ok({"closed": True, "saved": save})
        if _launched is not None and _launched.poll() is None:
            if not discard_changes:
                return {
                    "success": False,
                    "error_code": "BRIDGE_UNAVAILABLE",
                    "error": "The addon is not answering, so unsaved work cannot be checked. "
                    "Pass discard_changes=True to terminate the Blender this server started.",
                    "details": {"pid": _launched.pid},
                }
            _launched.terminate()
            _launched = None
            return ok({"closed": True, "terminated": True})
        return ok({"closed": False, "not_running": True})
