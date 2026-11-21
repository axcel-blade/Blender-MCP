"""Open and close the Blender application itself."""

from __future__ import annotations

import asyncio
import glob
import os
import re
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
# The saved file that was open when close_blender last quit Blender.
_last_file: str | None = None


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


_VERSION_IN_PATH = re.compile(r"(\d+\.\d+)")
_version_cache: dict[str, str | None] = {}


def _version_from_executable(exe: str) -> str | None:
    """``blender --version`` prints ``Blender 5.3.0`` first; cached per path."""
    if exe not in _version_cache:
        try:
            out = subprocess.run(  # noqa: S603
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                stdin=subprocess.DEVNULL,
            ).stdout
            match = re.search(r"Blender\s+(\d+\.\d+(?:\.\d+)?)", out or "")
            _version_cache[exe] = match.group(1) if match else None
        except (OSError, subprocess.SubprocessError):
            _version_cache[exe] = None
    return _version_cache[exe]


def blender_version(exe: str) -> str | None:
    """Version from the install folder name (``Blender 5.3``), else from the executable."""
    # Split on both separators: Path only knows the current OS's, so a Windows path
    # read on Linux (or the reverse) would otherwise be one long name.
    for part in reversed(re.split(r"[\\/]", exe)[:-1]):
        if "blender" in part.lower():
            match = _VERSION_IN_PATH.search(part)
            if match:
                return match.group(1)
    return _version_from_executable(exe)


def _version_key(version: str | None) -> tuple[int, ...]:
    return tuple(int(n) for n in version.split(".")) if version else ()


def list_installs() -> list[dict[str, Any]]:
    """Every Blender found on PATH and in the usual folders, newest version first."""
    seen: set[str] = set()
    installs: list[dict[str, Any]] = []
    found = [(shutil.which("blender"), "PATH")] + [
        (p, "install folder") for p in _candidate_paths()
    ]
    for exe, source in found:
        if not exe or not Path(exe).is_file():
            continue
        key = os.path.normcase(str(Path(exe).resolve()))
        if key in seen:
            continue
        seen.add(key)
        if "steamapps" in key:
            source = "Steam"
        installs.append({"path": exe, "version": blender_version(exe), "source": source})
    installs.sort(key=lambda i: _version_key(i["version"]), reverse=True)
    return installs


def _matches(version: str | None, wanted: str) -> bool:
    if not version:
        return False
    want = wanted.strip().split(".")
    return version.split(".")[: len(want)] == want


def find_blender(configured: str = "", version: str = "") -> str | None:
    """Pick the Blender executable: the configured path, else the newest install
    (or the newest matching ``version``, e.g. ``"5.3"``)."""
    if configured:
        return configured if Path(configured).is_file() else None
    installs = list_installs()
    if version:
        installs = [i for i in installs if _matches(i["version"], version)]
    return installs[0]["path"] if installs else None


def starting() -> bool:
    """True while a Blender this server launched is running but not yet answering."""
    return _launched is not None and _launched.poll() is None


async def _bridge_up(ctx: AppContext) -> bool:
    try:
        await ctx.bridge.ensure_connected()
        return ctx.bridge.connected
    except Exception:  # noqa: BLE001
        return False


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool(name="open_blender")
    async def open_blender(
        file_path: str = "",
        version: str = "",
        wait: bool = True,
        list_installs_only: bool = False,
        reopen_last: bool = False,
    ) -> dict[str, Any]:
        """Launch Blender when it is not running (no-op if the addon already answers).

        - ``file_path``: a .blend file to open
        - ``version``: which install to start, e.g. ``"5.3"`` (default: the newest)
        - ``wait``: return once the addon bridge accepts connections. With ``wait=False``
          it returns at once and ``get_addon_status`` reports ``blender: starting``
        - ``list_installs_only``: list the Blender installs found, without launching
        - ``reopen_last``: open the file that was open when ``close_blender`` last quit
          Blender (use it to restart Blender, e.g. after reinstalling the addon)

        Set BLENDER_MCP_BLENDER_PATH if Blender is not found."""
        global _launched
        if reopen_last and not file_path:
            if not _last_file:
                return {
                    "success": False,
                    "error_code": "NO_LAST_FILE",
                    "error": "No file to reopen: close_blender has not closed a saved file "
                    "since this server started.",
                    "details": {},
                }
            file_path = _last_file
        if list_installs_only:
            return ok({"installs": list_installs(), "configured": ctx.settings.blender_path})
        if await _bridge_up(ctx):
            return ok({"already_running": True, "launched": False})
        if starting():
            return ok(
                {"already_running": True, "launched": False, "starting": True},
                warning="Blender is still starting; call get_addon_status to see when it is ready.",
            )

        exe = find_blender(ctx.settings.blender_path, version)
        if not exe:
            if version and not ctx.settings.blender_path:
                return {
                    "success": False,
                    "error_code": "BLENDER_VERSION_NOT_FOUND",
                    "error": f"No Blender {version} install found.",
                    "details": {"installs": list_installs()},
                }
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

        # Detach so Blender outlives this server and never writes to its stdio.
        if sys.platform == "win32":
            proc: subprocess.Popen[bytes] = subprocess.Popen(  # noqa: S603
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            proc = subprocess.Popen(  # noqa: S603
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        _launched = proc

        result = {
            "launched": True,
            "pid": proc.pid,
            "executable": exe,
            "version": blender_version(exe),
        }
        if not wait:
            return ok(result)

        deadline = time.monotonic() + ctx.settings.blender_launch_timeout
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return {
                    "success": False,
                    "error_code": "BLENDER_EXITED",
                    "error": f"Blender exited during startup (code {proc.returncode})",
                    "details": result,
                }
            if await _bridge_up(ctx):
                return ok({**result, "bridge_ready": True})
            await asyncio.sleep(1.0)
        return ok(
            {**result, "bridge_ready": False, "starting": True},
            warning="Blender is running but the MCP addon has not answered yet. It may still "
            "be loading; call get_addon_status to check. If it never answers, make sure the "
            "addon is installed and enabled with auto-start on.",
        )

    @mcp.tool(name="close_blender")
    async def close_blender(save: bool = False, discard_changes: bool = False) -> dict[str, Any]:
        """Quit Blender. Refuses when there are unsaved changes unless ``save`` (save the
        current file first) or ``discard_changes`` is set. Ask the user before discarding."""
        global _launched, _last_file
        if await _bridge_up(ctx):
            reply = await call_blender(
                ctx, "quit_blender", {"save": save, "discard_changes": discard_changes}
            )
            if reply.get("success") is False:
                return reply
            await ctx.bridge.disconnect()
            _launched = None
            closed_file = (reply.get("result") or {}).get("filepath") or None
            if closed_file:
                _last_file = closed_file
            return ok({"closed": True, "saved": save, "file": closed_file})
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
