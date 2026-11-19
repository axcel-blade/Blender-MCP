"""Mesh modeling MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="edit_mesh")
    async def edit_mesh(
        name: str,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a structured mesh edit operation on an object."""
        return await call_blender(ctx, "edit_mesh", {"name": name, "operation": operation, "params": params or {}}, group="meshes")

    @mcp.tool(name="extrude_mesh")
    async def extrude_mesh(
        name: str,
        offset: list[float] | None = None,
    ) -> dict[str, Any]:
        """Extrude selected mesh geometry (object-mode helper)."""
        return await call_blender(ctx, "extrude_mesh", {"name": name, "offset": offset}, group="meshes")

    @mcp.tool(name="inset_faces")
    async def inset_faces(
        name: str,
        thickness: float = 0.1,
    ) -> dict[str, Any]:
        """Inset faces on a mesh object."""
        return await call_blender(ctx, "inset_faces", {"name": name, "thickness": thickness}, group="meshes")

    @mcp.tool(name="bevel_mesh")
    async def bevel_mesh(
        name: str,
        amount: float = 0.1,
        segments: int = 1,
    ) -> dict[str, Any]:
        """Bevel mesh edges."""
        return await call_blender(ctx, "bevel_mesh", {"name": name, "amount": amount, "segments": segments}, group="meshes")

    @mcp.tool(name="subdivide_mesh")
    async def subdivide_mesh(
        name: str,
        cuts: int = 1,
    ) -> dict[str, Any]:
        """Subdivide mesh faces."""
        return await call_blender(ctx, "subdivide_mesh", {"name": name, "cuts": cuts}, group="meshes")

    @mcp.tool(name="merge_vertices")
    async def merge_vertices(
        name: str,
        distance: float = 0.0001,
    ) -> dict[str, Any]:
        """Merge vertices by distance."""
        return await call_blender(ctx, "merge_vertices", {"name": name, "distance": distance}, group="meshes")

    @mcp.tool(name="delete_geometry")
    async def delete_geometry(
        name: str,
        mode: str = "VERT",
    ) -> dict[str, Any]:
        """Delete mesh geometry components."""
        return await call_blender(ctx, "delete_geometry", {"name": name, "mode": mode}, group="meshes")

    @mcp.tool(name="fill_faces")
    async def fill_faces(
        name: str,
    ) -> dict[str, Any]:
        """Fill selected boundary with faces where possible."""
        return await call_blender(ctx, "fill_faces", {"name": name}, group="meshes")

    @mcp.tool(name="triangulate_mesh")
    async def triangulate_mesh(
        name: str,
    ) -> dict[str, Any]:
        """Triangulate a mesh."""
        return await call_blender(ctx, "triangulate_mesh", {"name": name}, group="meshes")

    @mcp.tool(name="remesh_mesh")
    async def remesh_mesh(
        name: str,
        octree_depth: int = 4,
        mode: str = "SMOOTH",
    ) -> dict[str, Any]:
        """Apply remesh via modifier and apply it."""
        return await call_blender(ctx, "remesh_mesh", {"name": name, "octree_depth": octree_depth, "mode": mode}, group="meshes")

    @mcp.tool(name="decimate_mesh")
    async def decimate_mesh(
        name: str,
        ratio: float = 0.5,
    ) -> dict[str, Any]:
        """Decimate a mesh."""
        return await call_blender(ctx, "decimate_mesh", {"name": name, "ratio": ratio}, group="meshes")

    @mcp.tool(name="smooth_mesh")
    async def smooth_mesh(
        name: str,
        factor: float = 0.5,
        repeat: int = 1,
    ) -> dict[str, Any]:
        """Smooth mesh vertices."""
        return await call_blender(ctx, "smooth_mesh", {"name": name, "factor": factor, "repeat": repeat}, group="meshes")

    @mcp.tool(name="recalculate_normals")
    async def recalculate_normals(
        name: str,
        inside: bool = False,
    ) -> dict[str, Any]:
        """Recalculate mesh normals."""
        return await call_blender(ctx, "recalculate_normals", {"name": name, "inside": inside}, group="meshes")

    @mcp.tool(name="mesh_cleanup")
    async def mesh_cleanup(
        name: str,
    ) -> dict[str, Any]:
        """Run common mesh cleanup operations."""
        return await call_blender(ctx, "mesh_cleanup", {"name": name}, group="meshes")

