"""Object creation and modification MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="create_object")
    async def create_object(
        object_type: str,
        name: str | None = None,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a generic object by type."""
        return await call_blender(ctx, "create_object", {"object_type": object_type, "name": name, "location": location, "rotation": rotation, "scale": scale, "collection": collection}, group="objects")

    @mcp.tool(name="create_mesh")
    async def create_mesh(
        name: str | None = None,
        location: list[float] | None = None,
    ) -> dict[str, Any]:
        """Create an empty mesh object."""
        return await call_blender(ctx, "create_mesh", {"name": name, "location": location}, group="objects")

    @mcp.tool(name="create_primitive")
    async def create_primitive(
        primitive: str,
        name: str | None = None,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
        size: float | None = None,
        collection: str | None = None,
        smooth: bool = True,
    ) -> dict[str, Any]:
        """Create a mesh primitive (cube, uv_sphere, cylinder, ...)."""
        return await call_blender(ctx, "create_primitive", {"primitive": primitive, "name": name, "location": location, "rotation": rotation, "scale": scale, "size": size, "collection": collection, "smooth": smooth}, group="objects")

    @mcp.tool(name="create_cube")
    async def create_cube(
        name: str | None = None,
        location: list[float] | None = None,
        size: float = 2.0,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a cube."""
        return await call_blender(ctx, "create_cube", {"name": name, "location": location, "size": size, "collection": collection, "primitive": "cube"}, group="objects")

    @mcp.tool(name="create_sphere")
    async def create_sphere(
        name: str | None = None,
        location: list[float] | None = None,
        radius: float = 1.0,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a UV sphere."""
        return await call_blender(ctx, "create_sphere", {"name": name, "location": location, "radius": radius, "collection": collection, "primitive": "uv_sphere"}, group="objects")

    @mcp.tool(name="create_uv_sphere")
    async def create_uv_sphere(
        name: str | None = None,
        location: list[float] | None = None,
        radius: float = 1.0,
        segments: int = 32,
        rings: int = 16,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a UV sphere with segment/ring control."""
        return await call_blender(ctx, "create_uv_sphere", {"name": name, "location": location, "radius": radius, "segments": segments, "rings": rings, "collection": collection, "primitive": "uv_sphere"}, group="objects")

    @mcp.tool(name="create_ico_sphere")
    async def create_ico_sphere(
        name: str | None = None,
        location: list[float] | None = None,
        radius: float = 1.0,
        subdivisions: int = 2,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create an icosphere."""
        return await call_blender(ctx, "create_ico_sphere", {"name": name, "location": location, "radius": radius, "subdivisions": subdivisions, "collection": collection, "primitive": "ico_sphere"}, group="objects")

    @mcp.tool(name="create_cylinder")
    async def create_cylinder(
        name: str | None = None,
        location: list[float] | None = None,
        radius: float = 1.0,
        depth: float = 2.0,
        vertices: int = 32,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a cylinder."""
        return await call_blender(ctx, "create_cylinder", {"name": name, "location": location, "radius": radius, "depth": depth, "vertices": vertices, "collection": collection, "primitive": "cylinder"}, group="objects")

    @mcp.tool(name="create_cone")
    async def create_cone(
        name: str | None = None,
        location: list[float] | None = None,
        radius1: float = 1.0,
        radius2: float = 0.0,
        depth: float = 2.0,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a cone."""
        return await call_blender(ctx, "create_cone", {"name": name, "location": location, "radius1": radius1, "radius2": radius2, "depth": depth, "collection": collection, "primitive": "cone"}, group="objects")

    @mcp.tool(name="create_torus")
    async def create_torus(
        name: str | None = None,
        location: list[float] | None = None,
        major_radius: float = 1.0,
        minor_radius: float = 0.25,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a torus."""
        return await call_blender(ctx, "create_torus", {"name": name, "location": location, "major_radius": major_radius, "minor_radius": minor_radius, "collection": collection, "primitive": "torus"}, group="objects")

    @mcp.tool(name="create_plane")
    async def create_plane(
        name: str | None = None,
        location: list[float] | None = None,
        size: float = 2.0,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a plane."""
        return await call_blender(ctx, "create_plane", {"name": name, "location": location, "size": size, "collection": collection, "primitive": "plane"}, group="objects")

    @mcp.tool(name="create_circle")
    async def create_circle(
        name: str | None = None,
        location: list[float] | None = None,
        radius: float = 1.0,
        vertices: int = 32,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a circle."""
        return await call_blender(ctx, "create_circle", {"name": name, "location": location, "radius": radius, "vertices": vertices, "collection": collection, "primitive": "circle"}, group="objects")

    @mcp.tool(name="create_curve")
    async def create_curve(
        name: str | None = None,
        location: list[float] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a Bezier curve."""
        return await call_blender(ctx, "create_curve", {"name": name, "location": location, "collection": collection}, group="objects")

    @mcp.tool(name="create_text")
    async def create_text(
        text: str = "Text",
        name: str | None = None,
        location: list[float] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create a text object."""
        return await call_blender(ctx, "create_text", {"text": text, "name": name, "location": location, "collection": collection}, group="objects")

    @mcp.tool(name="create_empty")
    async def create_empty(
        name: str | None = None,
        location: list[float] | None = None,
        empty_display_type: str = "PLAIN_AXES",
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create an empty."""
        return await call_blender(ctx, "create_empty", {"name": name, "location": location, "empty_display_type": empty_display_type, "collection": collection}, group="objects")

    @mcp.tool(name="duplicate_object")
    async def duplicate_object(
        name: str,
        new_name: str | None = None,
        linked: bool = False,
    ) -> dict[str, Any]:
        """Duplicate an object."""
        return await call_blender(ctx, "duplicate_object", {"name": name, "new_name": new_name, "linked": linked}, group="objects")

    @mcp.tool(name="create_array_of_objects")
    async def create_array_of_objects(
        name: str,
        count: int = 3,
        offset: list[float] | None = None,
    ) -> dict[str, Any]:
        """Duplicate an object into an array along an offset."""
        return await call_blender(ctx, "create_array_of_objects", {"name": name, "count": count, "offset": offset}, group="objects")

    @mcp.tool(name="modify_object")
    async def modify_object(
        name: str,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
        dimensions: list[float] | None = None,
    ) -> dict[str, Any]:
        """Modify common object properties."""
        return await call_blender(ctx, "modify_object", {"name": name, "location": location, "rotation": rotation, "scale": scale, "dimensions": dimensions}, group="objects")

    @mcp.tool(name="move_object")
    async def move_object(
        name: str,
        location: list[float],
        space: str = "world",
    ) -> dict[str, Any]:
        """Move an object."""
        return await call_blender(ctx, "move_object", {"name": name, "location": location, "space": space}, group="objects")

    @mcp.tool(name="rotate_object")
    async def rotate_object(
        name: str,
        rotation: list[float],
        space: str = "world",
    ) -> dict[str, Any]:
        """Rotate an object (Euler radians)."""
        return await call_blender(ctx, "rotate_object", {"name": name, "rotation": rotation, "space": space}, group="objects")

    @mcp.tool(name="scale_object")
    async def scale_object(
        name: str,
        scale: list[float],
    ) -> dict[str, Any]:
        """Scale an object."""
        return await call_blender(ctx, "scale_object", {"name": name, "scale": scale}, group="objects")

    @mcp.tool(name="set_object_transform")
    async def set_object_transform(
        name: str,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> dict[str, Any]:
        """Set full object transform."""
        return await call_blender(ctx, "set_object_transform", {"name": name, "location": location, "rotation": rotation, "scale": scale}, group="objects")

    @mcp.tool(name="rename_object")
    async def rename_object(
        name: str,
        new_name: str,
    ) -> dict[str, Any]:
        """Rename an object."""
        return await call_blender(ctx, "rename_object", {"name": name, "new_name": new_name}, group="objects")

    @mcp.tool(name="set_object_origin")
    async def set_object_origin(
        name: str,
        origin_type: str = "ORIGIN_GEOMETRY",
    ) -> dict[str, Any]:
        """Set object origin."""
        return await call_blender(ctx, "set_object_origin", {"name": name, "origin_type": origin_type}, group="objects")

    @mcp.tool(name="set_object_visibility")
    async def set_object_visibility(
        name: str,
        hide_viewport: bool | None = None,
        hide_render: bool | None = None,
        hide_select: bool | None = None,
    ) -> dict[str, Any]:
        """Set object visibility flags."""
        return await call_blender(ctx, "set_object_visibility", {"name": name, "hide_viewport": hide_viewport, "hide_render": hide_render, "hide_select": hide_select}, group="objects")

    @mcp.tool(name="set_object_shading")
    async def set_object_shading(
        name: str,
        smooth: bool = True,
    ) -> dict[str, Any]:
        """Set smooth or flat shading."""
        return await call_blender(ctx, "set_object_shading", {"name": name, "smooth": smooth}, group="objects")

    @mcp.tool(name="set_object_parent")
    async def set_object_parent(
        name: str,
        parent: str,
        keep_transform: bool = True,
    ) -> dict[str, Any]:
        """Parent an object."""
        return await call_blender(ctx, "set_object_parent", {"name": name, "parent": parent, "keep_transform": keep_transform}, group="objects")

    @mcp.tool(name="unparent_object")
    async def unparent_object(
        name: str,
        keep_transform: bool = True,
    ) -> dict[str, Any]:
        """Unparent an object."""
        return await call_blender(ctx, "unparent_object", {"name": name, "keep_transform": keep_transform}, group="objects")

    @mcp.tool(name="join_objects")
    async def join_objects(
        names: list[str],
        target: str | None = None,
    ) -> dict[str, Any]:
        """Join multiple mesh objects."""
        return await call_blender(ctx, "join_objects", {"names": names, "target": target}, group="objects")

    @mcp.tool(name="separate_objects")
    async def separate_objects(
        name: str,
        mode: str = "LOOSE",
    ) -> dict[str, Any]:
        """Separate a mesh object."""
        return await call_blender(ctx, "separate_objects", {"name": name, "mode": mode}, group="objects")

    @mcp.tool(name="delete_object")
    async def delete_object(
        name: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Delete a single object (requires confirmed=true when confirm_destructive is on)."""
        return await call_blender(ctx, "delete_object", {"name": name, "confirmed": confirmed}, group="objects")

    @mcp.tool(name="delete_objects")
    async def delete_objects(
        names: list[str],
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Delete multiple objects by explicit names."""
        return await call_blender(ctx, "delete_objects", {"names": names, "confirmed": confirmed}, group="objects")

    @mcp.tool(name="apply_transform")
    async def apply_transform(
        name: str,
        location: bool = True,
        rotation: bool = True,
        scale: bool = True,
    ) -> dict[str, Any]:
        """Apply object transform."""
        return await call_blender(ctx, "apply_transform", {"name": name, "location": location, "rotation": rotation, "scale": scale}, group="objects")

    @mcp.tool(name="reset_transform")
    async def reset_transform(
        name: str,
        location: bool = True,
        rotation: bool = True,
        scale: bool = True,
    ) -> dict[str, Any]:
        """Reset object transform channels."""
        return await call_blender(ctx, "reset_transform", {"name": name, "location": location, "rotation": rotation, "scale": scale}, group="objects")

