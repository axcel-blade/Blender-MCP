"""Script execution MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.security.script_policy import ScriptPolicy
from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.utils.results import fail_from_exception, ok


def register(mcp: FastMCP, ctx: AppContext) -> None:
    policy = ScriptPolicy(ctx.settings)

    @mcp.tool(name="execute_blender_code")
    async def execute_blender_code(
        code: str,
        confirmed: bool = False,
        preview_only: bool = False,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Run Python in the live Blender with the full bpy API. The primary tool:
        anything Blender can do is reachable here.

        bpy, mathutils, C (bpy.context) and D (bpy.data) are preloaded. Returns the
        ``result`` variable if set, else the last expression's value, plus stdout and a
        traceback on error. Return dicts/lists. Batch related steps into one script.

        ``timeout``: seconds to allow (default 60, max 3600). Raise it for long work such
        as bakes or heavy booleans. A script that times out before starting is cancelled;
        one that already started keeps running in Blender, so check the scene before
        retrying.

        Warning: this is not a secure sandbox. It can access files, network, and
        system capabilities available to the Blender process.
        """
        try:
            policy.assert_can_execute(preview_only=preview_only, confirmed=confirmed)
            if preview_only:
                return ok(
                    {
                        "preview_only": True,
                        "code": code,
                        "warning": policy.warning_text(),
                        "mode": str(policy.mode),
                    }
                )
            params = {
                "code": code,
                "confirmed": confirmed,
                "preview_only": False,
                "timeout": timeout,
            }
            return await call_blender(ctx, "execute_blender_code", params, group="scripting")
        except Exception as exc:  # noqa: BLE001
            return fail_from_exception(exc)
