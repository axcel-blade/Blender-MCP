"""Screenshot / visual feedback MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="get_viewport_screenshot")
    async def get_viewport_screenshot(
        max_size: int | None = None,
        shading: str | None = None,
    ) -> dict[str, Any]:
        """Capture the 3D viewport as an image for visual verification."""
        return await call_blender(
            ctx,
            "get_viewport_screenshot",
            {"max_size": max_size, "shading": shading},
            group="screenshots",
        )

    @mcp.tool(name="capture_viewport")
    async def capture_viewport(
        max_size: int | None = None,
        view: str | None = None,
        shading: str | None = None,
    ) -> dict[str, Any]:
        """Capture the viewport with optional view/shading overrides."""
        return await call_blender(
            ctx,
            "capture_viewport",
            {"max_size": max_size, "view": view, "shading": shading},
            group="screenshots",
        )

    @mcp.tool(name="capture_camera_view")
    async def capture_camera_view(
        camera: str | None = None,
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """Capture from the active or named camera."""
        return await call_blender(
            ctx,
            "capture_camera_view",
            {"camera": camera, "max_size": max_size},
            group="screenshots",
        )

    @mcp.tool(name="capture_scene_preview")
    async def capture_scene_preview(
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """Capture a scene preview image."""
        return await call_blender(
            ctx, "capture_scene_preview", {"max_size": max_size}, group="screenshots"
        )

    @mcp.tool(name="capture_multiple_angles")
    async def capture_multiple_angles(
        angles: list[str] | None = None,
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """Capture multiple orthographic/perspective angles."""
        return await call_blender(
            ctx,
            "capture_multiple_angles",
            {"angles": angles, "max_size": max_size},
            group="screenshots",
        )

    @mcp.tool(name="capture_wireframe")
    async def capture_wireframe(
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """Capture a wireframe viewport image."""
        return await call_blender(
            ctx,
            "capture_wireframe",
            {"max_size": max_size, "shading": "WIREFRAME"},
            group="screenshots",
        )

    @mcp.tool(name="capture_material_preview")
    async def capture_material_preview(
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """Capture a material preview viewport image."""
        return await call_blender(
            ctx,
            "capture_material_preview",
            {"max_size": max_size, "shading": "MATERIAL"},
            group="screenshots",
        )

    @mcp.tool(name="capture_render")
    async def capture_render(
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """Capture or return the latest render preview."""
        return await call_blender(
            ctx, "capture_render", {"max_size": max_size}, group="screenshots"
        )

    @mcp.tool(name="inspect_render")
    async def inspect_render() -> dict[str, Any]:
        """Return metadata about the latest captured/rendered image."""
        return await call_blender(ctx, "inspect_render", {}, group="screenshots")
