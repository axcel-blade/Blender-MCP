"""Register reusable MCP prompts / workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt()
    def create_product_model(description: str) -> str:
        return (
            f"Create a realistic product model for: {description}\\n"
            "1) Inspect the scene and create a dedicated collection.\\n"
            "2) Block out major forms with named objects.\\n"
            "3) Add details, materials, studio lighting, and a camera.\\n"
            "4) Capture viewport screenshots, fix issues, then report."
        )

    @mcp.prompt()
    def create_environment(description: str) -> str:
        return (
            f"Create a detailed environment: {description}\\n"
            "Build geometry, materials, lighting, and camera. Organize into "
            "Environment/Props/Lighting/Cameras collections. Verify visually."
        )

    @mcp.prompt()
    def create_low_poly_scene(description: str) -> str:
        return (
            f"Create a stylized low-poly scene: {description}\\n"
            "Prefer simple primitives, flat colors, limited polycounts, and clear silhouettes."
        )

    @mcp.prompt()
    def create_character(description: str) -> str:
        return (
            f"Create a character blockout: {description}\\n"
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
