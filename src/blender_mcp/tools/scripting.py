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
        """Execute Python code inside Blender when script permissions allow it.

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
