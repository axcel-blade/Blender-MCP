"""MCP server entrypoints."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from blender_mcp import __version__
from blender_mcp.config import Settings, load_settings
from blender_mcp.logging_config import setup_logging
from blender_mcp.prompts.registry import register_prompts
from blender_mcp.protocol.client import BlenderBridgeClient
from blender_mcp.resources.registry import register_resources
from blender_mcp.tools.registry import AppContext, apply_tool_profile, register_all_tools

INSTRUCTIONS = """
Blender MCP drives the user's live Blender. execute_blender_code runs Python there with the
full bpy API (bpy, mathutils, C=bpy.context, D=bpy.data preloaded), so anything Blender can
do, you can do. look shows you the result (mode="render" for a real render). Use both freely.

Start: get_addon_status (versions, warnings, libraries, generators), then get_scene_info.

execute_blender_code returns the `result` variable if you set one, else the value of the
last expression, plus stdout and a traceback on error. Return dicts/lists, not prints.
Batch related work into one script; read the traceback and retry instead of guessing.

Unsure of a property, enum value, operator argument or node socket? lookup_api reads it
from the user's own Blender (e.g. "RenderSettings.engine", "ShaderNodeBsdfPrincipled",
"bpy.ops.mesh.bevel", or search words), so it always matches their version.

Scripts run in someone else's Blender, so:
- Find shader nodes by type, never by name (names are localized):
  `next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")`.
- Principled BSDF input names changed in 4.x ("Specular" -> "Specular IOR Level",
  "Emission" -> "Emission Color"); check `"X" in node.inputs` before setting.
- Never hardcode enum identifiers; read them, e.g.
  `[i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]`.
  Assign scene.render.engine inside try/except TypeError; the message lists valid engines.
- Material color goes on shader node inputs; material.diffuse_color is viewport-only.
- Prefer bpy.data over bpy.ops. Operators depend on mode, active object and selection:
  set them explicitly or use bpy.context.temp_override(...).
- Call bpy.context.view_layer.update() before reading matrix_world or evaluated data.
- In Edit Mode use bmesh and bmesh.update_edit_mesh(); new bpy.data objects must be
  linked to a collection to appear.
- Blender is Z-up, meters by default.

A reply with `user_edits` means the user changed the scene by hand since your last call
(objects added, removed, moved or edited; selection, mode or frame). Treat that as their
intent: build on it, and don't undo or overwrite it unless they ask.

Work like an artist: inspect first, put new work in its own named collection, never delete
or overwrite the user's objects unless asked, then look (mode=material or rendered for
color/lighting, angles for proportions), fix, and look again before reporting done.
Images stay in context: max_size 384-512 is plenty for layout checks.

Assets: search_assets, then import_external_asset (Poly Haven, Sketchfab, Poly Pizza).
generate_3d makes ONE new textured model from text or an image (1-3 min, may cost a
credit), never a whole scene or the ground. Imported and generated models arrive at
arbitrary scale: read their world bounding box, scale them, and set them on the ground.
Realism: when the user asks for anything realistic, photoreal or lifelike, read
get_guide("realism") first. Never deliver plain primitives with flat colors: use scanned
assets, beveled geometry, PBR textures with roughness/normal detail, an HDRI or physical sky,
area lights, Cycles, AgX and a real-lens camera, then check in rendered mode.
Stylised, cinematic or concept-art requests (often from a reference image): read
get_guide("cinematic") instead and work in stages: blockout, main structures, detail,
materials, sky and lighting, compositing. After each stage run look(mode="render") (a real
render with the compositor applied), compare it with the reference, list the three biggest
differences, fix them, then stop and wait for the user's feedback before the next stage.
The recreate_reference prompt spells this out.
More reference: get_guide (bpy, materials, scene, workflows, realism, cinematic).
""".strip()


def create_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or load_settings()
    setup_logging(settings.log_level, settings.log_file)

    bridge = BlenderBridgeClient(settings.bridge())
    ctx = AppContext(settings=settings, bridge=bridge)

    mcp = FastMCP(
        name="Blender MCP",
        instructions=INSTRUCTIONS,
    )

    register_all_tools(mcp, ctx)
    register_resources(mcp, ctx)
    register_prompts(mcp)

    @mcp.tool(name="blender_mcp_version")
    async def blender_mcp_version() -> dict:
        """Return Blender MCP server version and bridge configuration (no secrets)."""
        return {
            "success": True,
            "result": {
                "version": __version__,
                "host": settings.host,
                "port": settings.port,
                "safe_execution_mode": settings.safe_execution_mode,
                "script_permission": str(settings.script_permission),
                "tool_profile": settings.tool_profile,
                "tool_groups": settings.tool_groups.model_dump(),
                "auth_configured": bool(settings.auth_token),
            },
        }

    apply_tool_profile(mcp, settings.tool_profile)
    return mcp


def main() -> None:
    """Stdio MCP entrypoint used by the console script."""
    settings = load_settings()
    mcp = create_server(settings)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
