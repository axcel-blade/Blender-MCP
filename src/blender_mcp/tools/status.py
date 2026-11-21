"""Addon status, guides and scene search tools."""

from __future__ import annotations

from importlib import resources
from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp import __version__
from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.utils.results import ok

# Commands newer server features rely on; missing ones mean the addon is outdated.
REQUIRED_COMMANDS = (
    "import_local_asset",
    "lookup_api",
    "quit_blender",
    "blend_file_info",
    "rename_blend_file",
    "save_copy",
    "recent_blend_files",
    "recover_blend_file",
)


def list_guides() -> list[str]:
    return sorted(
        p.name.removesuffix(".md")
        for p in resources.files("blender_mcp.guides").iterdir()
        if p.name.endswith(".md")
    )


def read_guide(name: str) -> str:
    if name not in list_guides():
        raise ValueError(f"Unknown guide {name!r}; available: {', '.join(list_guides())}")
    return (resources.files("blender_mcp.guides") / f"{name}.md").read_text(encoding="utf-8")


def addon_warnings(info: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    addon_version = info.get("addon_version")
    if addon_version and addon_version != __version__:
        warnings.append(
            f"Addon version {addon_version} differs from server {__version__}. "
            "Reinstall the addon: `blender-mcp install-addon`, then restart Blender."
        )
    commands = info.get("commands")
    if commands is not None:
        missing = [c for c in REQUIRED_COMMANDS if c not in commands]
        if missing:
            warnings.append(
                "Addon is outdated (missing: " + ", ".join(missing) + "). "
                "Reinstall it with `blender-mcp install-addon`."
            )
    return warnings


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool(name="get_addon_status")
    async def get_addon_status() -> dict[str, Any]:
        """Start here: Blender/addon versions, connection, enabled asset libraries and
        3D generators, and warnings such as an outdated addon."""
        p = ctx.settings.providers()
        providers = {
            "polyhaven": p.polyhaven,
            "sketchfab": p.sketchfab and bool(p.sketchfab_api_key),
            "polypizza": p.polypizza and bool(p.polypizza_api_key),
        }
        generators = {
            "meshy": p.meshy and bool(p.meshy_api_key),
            "tripo": p.tripo and bool(p.tripo_api_key),
        }
        from blender_mcp.tools import app

        if app.starting() and not ctx.bridge.connected:
            return ok(
                {
                    "server_version": __version__,
                    "blender": "starting",
                    "asset_libraries": providers,
                    "generators": generators,
                },
                warning="Blender is still starting; check again in a few seconds.",
            )
        diag = await call_blender(ctx, "diagnose_blender_connection", {}, group="scene")
        if diag.get("success") is False:
            return {
                **diag,
                "server_version": __version__,
                "asset_libraries": providers,
                "generators": generators,
            }
        info = diag.get("result", diag)
        info = dict(info) if isinstance(info, dict) else {}
        status = ok(
            {
                "server_version": __version__,
                "blender_version": info.get("blender_version"),
                "addon_version": info.get("addon_version"),
                "script_permission": info.get("script_permission"),
                "asset_libraries": providers,
                "generators": generators,
                "guides": list_guides(),
                "warnings": addon_warnings(info),
            }
        )
        if diag.get("user_edits"):
            status["user_edits"] = diag["user_edits"]
        return status

    @mcp.tool(name="get_guide")
    async def get_guide(name: str) -> dict[str, Any]:
        """Read a short how-to guide (bpy, materials, scene); unknown names list them."""
        try:
            return ok({"name": name, "guide": read_guide(name)})
        except ValueError as exc:
            return {"success": False, "error": str(exc), "guides": list_guides()}

    @mcp.tool(name="lookup_api")
    async def lookup_api(query: str) -> dict[str, Any]:
        """Look up the Blender Python API in the user's running Blender, so names match
        their version. Use it before writing bpy code you are unsure of.

        ``query`` is either an identifier or search words:
        - a type: ``Scene``, ``bpy.types.RenderSettings`` (properties with types,
          defaults, enum identifiers; node types also list their input/output sockets,
          e.g. ``ShaderNodeBsdfPrincipled``)
        - a member: ``bpy.types.RenderSettings.engine``, ``Object.modifiers``
        - an operator: ``bpy.ops.mesh.primitive_cube_add`` (its arguments)
        - a Python module or function: ``mathutils.Vector``, ``bmesh.ops.bevel``
        - words: ``bevel modifier width`` (matching types, properties and operators)
        """
        return await call_blender(ctx, "lookup_api", {"query": query}, group="scene")

    @mcp.tool(name="search_scene")
    async def search_scene(query: str = "", limit: int = 30) -> dict[str, Any]:
        """Find objects whose name contains ``query`` (case-insensitive)."""
        return await call_blender(
            ctx,
            "get_objects",
            {"name_filter": query, "limit": max(1, min(limit, 200))},
            group="scene",
        )

    for guide in list_guides():

        def _make(name: str):
            def _resource() -> str:
                return read_guide(name)

            _resource.__name__ = f"guide_{name}"
            _resource.__doc__ = f"Blender MCP guide: {name}"
            return _resource

        mcp.resource(f"blender://guides/{guide}")(_make(guide))
