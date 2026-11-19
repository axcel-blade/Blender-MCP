"""Material MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="create_material")
    async def create_material(
        name: str | None = None,
        base_color: list[float] | None = None,
        metallic: float = 0.0,
        roughness: float = 0.5,
    ) -> dict[str, Any]:
        """Create a Principled BSDF material."""
        return await call_blender(
            ctx,
            "create_material",
            {"name": name, "base_color": base_color, "metallic": metallic, "roughness": roughness},
            group="materials",
        )

    @mcp.tool(name="assign_material")
    async def assign_material(
        object_name: str,
        material_name: str,
        slot: int = 0,
    ) -> dict[str, Any]:
        """Assign a material to an object."""
        return await call_blender(
            ctx,
            "assign_material",
            {"object_name": object_name, "material_name": material_name, "slot": slot},
            group="materials",
        )

    @mcp.tool(name="remove_material")
    async def remove_material(
        object_name: str,
        slot: int = 0,
    ) -> dict[str, Any]:
        """Remove a material slot from an object."""
        return await call_blender(
            ctx, "remove_material", {"object_name": object_name, "slot": slot}, group="materials"
        )

    @mcp.tool(name="modify_material")
    async def modify_material(
        name: str,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        """Modify Principled BSDF inputs on a material."""
        return await call_blender(
            ctx, "modify_material", {"name": name, "settings": settings}, group="materials"
        )

    @mcp.tool(name="get_material_info")
    async def get_material_info(
        name: str,
    ) -> dict[str, Any]:
        """Inspect a material and its nodes."""
        return await call_blender(ctx, "get_material_info", {"name": name}, group="materials")

    @mcp.tool(name="list_materials")
    async def list_materials() -> dict[str, Any]:
        """List all materials."""
        return await call_blender(ctx, "list_materials", {}, group="materials")

    @mcp.tool(name="set_material_color")
    async def set_material_color(
        name: str,
        color: list[float],
    ) -> dict[str, Any]:
        """Set material base color."""
        return await call_blender(
            ctx, "set_material_color", {"name": name, "color": color}, group="materials"
        )

    @mcp.tool(name="set_material_properties")
    async def set_material_properties(
        name: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Set common Principled BSDF properties."""
        return await call_blender(
            ctx,
            "set_material_properties",
            {"name": name, "properties": properties},
            group="materials",
        )

    @mcp.tool(name="create_basic_shader")
    async def create_basic_shader(
        name: str | None = None,
        color: list[float] | None = None,
    ) -> dict[str, Any]:
        """Create a basic Principled material."""
        return await call_blender(
            ctx, "create_basic_shader", {"name": name, "color": color}, group="materials"
        )

    @mcp.tool(name="create_emission_material")
    async def create_emission_material(
        name: str | None = None,
        color: list[float] | None = None,
        strength: float = 5.0,
    ) -> dict[str, Any]:
        """Create an emission material."""
        return await call_blender(
            ctx,
            "create_emission_material",
            {"name": name, "color": color, "strength": strength},
            group="materials",
        )

    @mcp.tool(name="create_metallic_material")
    async def create_metallic_material(
        name: str | None = None,
        color: list[float] | None = None,
        roughness: float = 0.2,
    ) -> dict[str, Any]:
        """Create a metallic material."""
        return await call_blender(
            ctx,
            "create_metallic_material",
            {"name": name, "color": color, "roughness": roughness},
            group="materials",
        )

    @mcp.tool(name="create_glass_material")
    async def create_glass_material(
        name: str | None = None,
        ior: float = 1.45,
        roughness: float = 0.0,
    ) -> dict[str, Any]:
        """Create a glass material."""
        return await call_blender(
            ctx,
            "create_glass_material",
            {"name": name, "ior": ior, "roughness": roughness},
            group="materials",
        )

    @mcp.tool(name="create_transparent_material")
    async def create_transparent_material(
        name: str | None = None,
        alpha: float = 0.3,
        color: list[float] | None = None,
    ) -> dict[str, Any]:
        """Create a transparent material."""
        return await call_blender(
            ctx,
            "create_transparent_material",
            {"name": name, "alpha": alpha, "color": color},
            group="materials",
        )

    @mcp.tool(name="get_material_nodes")
    async def get_material_nodes(
        name: str,
    ) -> dict[str, Any]:
        """List nodes in a material node tree."""
        return await call_blender(ctx, "get_material_nodes", {"name": name}, group="materials")

    @mcp.tool(name="set_material_nodes")
    async def set_material_nodes(
        name: str,
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply structured node operations to a material."""
        return await call_blender(
            ctx, "set_material_nodes", {"name": name, "operations": operations}, group="materials"
        )

    @mcp.tool(name="assign_texture")
    async def assign_texture(
        material_name: str,
        image_path: str,
        input_name: str = "Base Color",
    ) -> dict[str, Any]:
        """Assign an image texture to a material input."""
        return await call_blender(
            ctx,
            "assign_texture",
            {"material_name": material_name, "image_path": image_path, "input_name": input_name},
            group="materials",
        )
