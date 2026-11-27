"""Register reusable MCP prompts / workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt()
    def create_product_model(description: str) -> str:
        return (
            f"Create a realistic product model for: {description}\n"
            "Read get_guide('realism') first and follow it.\n"
            "1) Inspect the scene and create a dedicated collection.\n"
            "2) Search Poly Haven/Sketchfab for a real model; otherwise model it at real "
            "scale with bevels and subdivision.\n"
            "3) PBR materials with roughness and normal detail, HDRI plus area-light studio "
            "lighting, Cycles, AgX, an 85-100 mm camera with depth of field.\n"
            "4) Look in rendered mode, fix the least realistic thing, repeat, then report."
        )

    @mcp.prompt()
    def create_environment(description: str) -> str:
        return (
            f"Create a detailed environment: {description}\n"
            "Unless a stylized look is requested, aim for realism: read get_guide('realism'), "
            "prefer scanned assets and PBR textures, HDRI/physical sky, Cycles and AgX. "
            "Build geometry, materials, lighting, and camera. Organize into "
            "Environment/Props/Lighting/Cameras collections. Verify visually."
        )

    @mcp.prompt()
    def create_realistic_scene(description: str) -> str:
        return (
            f"Create a photorealistic scene: {description}\n"
            "Read get_guide('realism') and follow every section.\n"
            "1) Inspect the scene; work in a new collection at real-world scale.\n"
            "2) Import scanned assets, HDRIs and PBR textures (search_assets) before modeling "
            "anything from primitives; bevel every hard edge you model.\n"
            "3) No flat colors: textures or procedural materials with roughness and bump.\n"
            "4) HDRI or physical sky + area key light, Cycles with denoising, AgX.\n"
            "5) Camera at eye height, 35-50 mm, depth of field.\n"
            "6) look in rendered mode, fix the least realistic thing, look again, then report."
        )

    @mcp.prompt()
    def recreate_reference(description: str = "the attached reference image") -> str:
        return (
            f"Recreate this reference as a stylised, cinematic Blender scene: {description}\n"
            "Read get_guide('cinematic') first (use get_guide('realism') instead only if the "
            "user wants photorealism). Inspect the scene and work in new named collections.\n"
            "Work in six stages, in order:\n"
            "1) Blockout: match the reference camera (aspect, focal length, horizon) and "
            "block every large mass with primitives.\n"
            "2) Main structures: terrain, cliffs, islands, tracks and bridges; import or "
            "generate_3d complex hero objects.\n"
            "3) Detail: secondary shapes, props, breakup of silhouettes.\n"
            "4) Materials: stylised, emissive and wet materials.\n"
            "5) Sky and lighting: sky, fog/volumes, key light, lightning, rain.\n"
            "6) Compositing: glare, colour grading, vignette.\n"
            "After EVERY stage: look(mode='render', max_size=512); compare it with the "
            "reference; list the three biggest differences (composition, value/colour, "
            "shape); fix them and render again; then show the user the render and the list, "
            "and wait for their feedback before starting the next stage."
        )

    @mcp.prompt()
    def create_low_poly_scene(description: str) -> str:
        return (
            f"Create a stylized low-poly scene: {description}\n"
            "Prefer simple primitives, flat colors, limited polycounts, and clear silhouettes."
        )

    @mcp.prompt()
    def create_character(description: str) -> str:
        return (
            f"Create a character blockout: {description}\n"
            "Use proportional primitives, meaningful names, and a Characters collection."
        )

    @mcp.prompt()
    def improve_scene() -> str:
        return (
            "Inspect the current Blender scene, identify visual and structural issues, "
            "propose concrete improvements, then apply the highest-impact fixes and verify."
        )

    @mcp.prompt()
    def optimize_scene() -> str:
        return (
            "Optimize geometry, materials, object count, modifiers, and render settings "
            "while preserving visual intent. Report before/after metrics."
        )

    @mcp.prompt()
    def lighting_artist() -> str:
        return (
            "Analyze current lighting, improve it with an appropriate preset or custom lights, "
            "and capture before/after screenshots."
        )

    @mcp.prompt()
    def material_artist() -> str:
        return (
            "Improve materials using Principled BSDF. Prefer node-based materials, "
            "consistent roughness/metallic values, and visual verification."
        )

    @mcp.prompt()
    def scene_inspector() -> str:
        return (
            "Produce a structured report of objects, collections, materials, lights, cameras, "
            "animation, and render settings. Flag problems."
        )

    @mcp.prompt()
    def render_preparation() -> str:
        return (
            "Prepare the project for a high-quality render: camera, lighting, samples, "
            "resolution, output path, and a preview render before final."
        )
