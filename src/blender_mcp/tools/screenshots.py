"""Screenshot / visual feedback MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.utils.results import to_image_content

LOOK_MODES = ("viewport", "camera", "angles", "wireframe", "material", "rendered")


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="look")
    async def look(
        mode: str = "viewport",
        view: str | None = None,
        camera: str | None = None,
        angles: list[str] | None = None,
        max_size: int = 768,
    ) -> list[Any]:
        """See the scene. Use after every visible change, then fix what looks wrong.

        mode: viewport (current 3D view, solid) | material (textures/colors) |
        rendered (lights + render engine) | wireframe | camera (through the active or
        named ``camera``) | angles (several views in one call; ``angles`` defaults to
        FRONT, RIGHT, TOP, PERSPECTIVE).
        view: FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM, CAMERA (viewport modes only).
        max_size: longest image edge in px. Images stay in context, so 384-512 is enough
        for layout checks; go higher only for fine detail.
        """
        mode = (mode or "viewport").lower()
        if mode not in LOOK_MODES:
            return to_image_content(
                {"success": False, "error": f"mode must be one of {', '.join(LOOK_MODES)}"}
            )
        size = max(128, min(int(max_size), ctx.settings.screenshot_max_size * 2))
        if mode == "camera":
            command, params = "capture_camera_view", {"camera": camera, "max_size": size}
        elif mode == "angles":
            command, params = "capture_multiple_angles", {"angles": angles, "max_size": size}
        else:
            shading = {
                "viewport": None,
                "wireframe": "WIREFRAME",
                "material": "MATERIAL",
                "rendered": "RENDERED",
            }[mode]
            command = "capture_viewport"
            params = {"max_size": size, "view": view, "shading": shading}
        return to_image_content(await call_blender(ctx, command, params, group="screenshots"))

    @mcp.tool(name="get_viewport_screenshot")
    async def get_viewport_screenshot(
        max_size: int | None = None,
        shading: str | None = None,
    ) -> list[Any]:
        """Capture the 3D viewport as an image for visual verification."""
        return to_image_content(
            await call_blender(
                ctx,
                "get_viewport_screenshot",
                {"max_size": max_size, "shading": shading},
                group="screenshots",
            )
        )

    @mcp.tool(name="capture_viewport")
    async def capture_viewport(
        max_size: int | None = None,
        view: str | None = None,
        shading: str | None = None,
    ) -> list[Any]:
        """Capture the viewport with optional view/shading overrides."""
        return to_image_content(
            await call_blender(
                ctx,
                "capture_viewport",
                {"max_size": max_size, "view": view, "shading": shading},
                group="screenshots",
            )
        )

    @mcp.tool(name="capture_camera_view")
    async def capture_camera_view(
        camera: str | None = None,
        max_size: int | None = None,
    ) -> list[Any]:
        """Capture from the active or named camera."""
        return to_image_content(
            await call_blender(
                ctx,
                "capture_camera_view",
                {"camera": camera, "max_size": max_size},
                group="screenshots",
            )
        )

    @mcp.tool(name="capture_scene_preview")
    async def capture_scene_preview(
        max_size: int | None = None,
    ) -> list[Any]:
        """Capture a scene preview image."""
        return to_image_content(
            await call_blender(
                ctx, "capture_scene_preview", {"max_size": max_size}, group="screenshots"
            )
        )

    @mcp.tool(name="capture_multiple_angles")
    async def capture_multiple_angles(
        angles: list[str] | None = None,
        max_size: int | None = None,
    ) -> list[Any]:
        """Capture multiple orthographic/perspective angles."""
        return to_image_content(
            await call_blender(
                ctx,
                "capture_multiple_angles",
                {"angles": angles, "max_size": max_size},
                group="screenshots",
            )
        )

    @mcp.tool(name="capture_wireframe")
    async def capture_wireframe(
        max_size: int | None = None,
    ) -> list[Any]:
        """Capture a wireframe viewport image."""
        return to_image_content(
            await call_blender(
                ctx,
                "capture_wireframe",
                {"max_size": max_size, "shading": "WIREFRAME"},
                group="screenshots",
            )
        )

    @mcp.tool(name="capture_material_preview")
    async def capture_material_preview(
        max_size: int | None = None,
    ) -> list[Any]:
        """Capture a material preview viewport image."""
        return to_image_content(
            await call_blender(
                ctx,
                "capture_material_preview",
                {"max_size": max_size, "shading": "MATERIAL"},
                group="screenshots",
            )
        )

    @mcp.tool(name="capture_render")
    async def capture_render(
        max_size: int | None = None,
    ) -> list[Any]:
        """Capture or return the latest render preview."""
        return to_image_content(
            await call_blender(ctx, "capture_render", {"max_size": max_size}, group="screenshots")
        )

    @mcp.tool(name="inspect_render")
    async def inspect_render() -> list[Any]:
        """Return metadata about the latest captured/rendered image."""
        return to_image_content(await call_blender(ctx, "inspect_render", {}, group="screenshots"))
