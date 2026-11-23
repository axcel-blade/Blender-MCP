"""Extra modeling, CAD-style, procedural geometry-node and shader-node MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender, call_blender_paths
from blender_mcp.tools.registry import forward_params as P

MaterialPreset = Literal[
    "chrome",
    "polished_metal",
    "brushed_metal",
    "gold",
    "copper",
    "rust",
    "glass",
    "frosted_glass",
    "water",
    "plastic",
    "glossy_plastic",
    "rubber",
    "car_paint",
    "ceramic",
    "wood",
    "marble",
    "concrete",
    "brick",
    "fabric",
    "leather",
    "skin",
    "ground",
    "grass",
    "sand",
    "snow",
    "rock",
    "neon",
    "hologram",
]


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="boolean_operation")
    async def boolean_operation(
        target: str,
        cutter: str,
        operation: Literal["DIFFERENCE", "UNION", "INTERSECT"] = "DIFFERENCE",
        solver: Literal["EXACT", "FAST", "MANIFOLD"] = "EXACT",
        apply: bool = False,
        hide_cutter: bool = True,
    ) -> dict[str, Any]:
        """Boolean cut/union/intersect. Non-destructive unless apply=true."""
        return await call_blender(ctx, "boolean_operation", P(locals()), group="meshes")

    @mcp.tool(name="loop_cut")
    async def loop_cut(
        name: str, axis: Literal["X", "Y", "Z"] = "Z", cuts: int = 1
    ) -> dict[str, Any]:
        """Add evenly spaced edge loops across an axis."""
        return await call_blender(ctx, "loop_cut", P(locals()), group="meshes")

    @mcp.tool(name="bisect_mesh")
    async def bisect_mesh(
        name: str,
        plane_co: list[float] | None = None,
        plane_no: list[float] | None = None,
        clear_inner: bool = False,
        clear_outer: bool = False,
        fill: bool = False,
    ) -> dict[str, Any]:
        """Knife/bisect along a world-space plane; clear a side and cap the cut with fill=true."""
        return await call_blender(ctx, "bisect_mesh", P(locals()), group="meshes")

    @mcp.tool(name="bridge_edge_loops")
    async def bridge_edge_loops(
        name: str, use_pairs: bool = False, twist: int = 0, segments: int = 1
    ) -> dict[str, Any]:
        """Bridge open boundary loops of a mesh (connect tube ends, close gaps)."""
        return await call_blender(ctx, "bridge_edge_loops", P(locals()), group="meshes")

    @mcp.tool(name="dissolve_geometry")
    async def dissolve_geometry(
        name: str,
        mode: Literal["limited", "degenerate", "vertices", "edges", "faces"] = "limited",
        angle: float = 5.0,
        distance: float | None = None,
        indices: list[int] | None = None,
    ) -> dict[str, Any]:
        """Dissolve geometry: limited (planar cleanup), degenerate, or by element indices."""
        return await call_blender(ctx, "dissolve_geometry", P(locals()), group="meshes")

    @mcp.tool(name="add_mesh_elements")
    async def add_mesh_elements(
        name: str,
        vertices: list[list[float]],
        edges: list[list[int]] | None = None,
        faces: list[list[int]] | None = None,
        connect_existing: bool = False,
        merge_distance: float | None = None,
    ) -> dict[str, Any]:
        """Add vertices/edges/faces to a mesh (indices refer to the new vertices)."""
        return await call_blender(ctx, "add_mesh_elements", P(locals()), group="meshes")

    @mcp.tool(name="spin_mesh")
    async def spin_mesh(
        name: str,
        axis: Literal["X", "Y", "Z"] = "Z",
        angle: float = 360,
        steps: int = 32,
        center: list[float] | None = None,
    ) -> dict[str, Any]:
        """Lathe a profile into a solid of revolution (vases, bottles, columns, wheels)."""
        return await call_blender(ctx, "spin_mesh", P(locals()), group="meshes")

    @mcp.tool(name="set_object_dimensions")
    async def set_object_dimensions(
        name: str,
        dimensions: list[float | None],
        keep_proportions: bool = False,
        apply_scale: bool = False,
    ) -> dict[str, Any]:
        """CAD-style exact size in scene units ([x, y, z]; null keeps an axis)."""
        return await call_blender(ctx, "set_object_dimensions", P(locals()), group="objects")

    @mcp.tool(name="set_scene_units")
    async def set_scene_units(
        system: Literal["METRIC", "IMPERIAL", "NONE"] = "METRIC",
        length_unit: str | None = None,
        scale_length: float | None = None,
        mass_unit: str | None = None,
    ) -> dict[str, Any]:
        """Unit system and length unit (MILLIMETERS, CENTIMETERS, METERS, INCHES, FEET...)."""
        return await call_blender(ctx, "set_scene_units", P(locals()), group="scene")

    @mcp.tool(name="measure")
    async def measure(
        a: str | list[float] | None = None,
        b: str | list[float] | None = None,
        objects: list[str] | None = None,
    ) -> dict[str, Any]:
        """Distance between objects/points and per-object dimensions, volume and surface area."""
        return await call_blender(ctx, "measure", P(locals()), group="scene")

    @mcp.tool(name="array_along_curve")
    async def array_along_curve(
        name: str,
        curve: str,
        offset: list[float] | None = None,
        axis: Literal["POS_X", "POS_Y", "POS_Z", "NEG_X", "NEG_Y", "NEG_Z"] = "POS_X",
    ) -> dict[str, Any]:
        """Repeat and bend an object along a curve (chains, fences, rails, cables)."""
        return await call_blender(ctx, "array_along_curve", P(locals()), group="modifiers")

    # ------------------------------------------------------------------ geometry nodes

    @mcp.tool(name="create_gn_scatter")
    async def create_gn_scatter(
        surface: str,
        instance_collection: str,
        density: float = 1.0,
        scale_range: list[float] | None = None,
        align_to_normal: bool = False,
        hide_source_collection: bool = True,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Non-destructive Geometry Nodes scattering/instancing system (exposes Density and
        Seed)."""
        return await call_blender(ctx, "create_gn_scatter", P(locals()), group="geometry_nodes")

    @mcp.tool(name="create_parametric_object")
    async def create_parametric_object(
        kind: Literal["gear", "pipe", "helix", "grid_panel"] = "gear",
        name: str | None = None,
        teeth: int | None = None,
        radius: float | None = None,
        thickness: float | None = None,
        length: float | None = None,
        turns: float | None = None,
        size_x: float | None = None,
        size_y: float | None = None,
        holes: int | None = None,
        location: list[float] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Geometry-nodes parametric asset whose parameters stay editable as modifier inputs."""
        return await call_blender(
            ctx, "create_parametric_object", P(locals()), group="geometry_nodes"
        )

    @mcp.tool(name="remove_geometry_node")
    async def remove_geometry_node(node_group: str, node: str) -> dict[str, Any]:
        """Delete a node from a geometry node group."""
        return await call_blender(ctx, "remove_geometry_node", P(locals()), group="geometry_nodes")

    # ------------------------------------------------------------------ shader nodes

    @mcp.tool(name="add_shader_node")
    async def add_shader_node(
        material: str,
        node_type: str,
        name: str | None = None,
        location: list[float] | None = None,
        inputs: dict[str, Any] | None = None,
        properties: dict[str, Any] | None = None,
        create_material: bool = False,
    ) -> dict[str, Any]:
        """Add a shader node by bl_idname (ShaderNodeTexNoise, ShaderNodeMix, ShaderNodeBump,
        ...)."""
        return await call_blender(ctx, "add_shader_node", P(locals()), group="materials")

    @mcp.tool(name="connect_shader_nodes")
    async def connect_shader_nodes(
        material: str,
        from_node: str,
        to_node: str,
        from_socket: str | int = 0,
        to_socket: str | int = 0,
    ) -> dict[str, Any]:
        """Link shader node sockets by name or index."""
        return await call_blender(ctx, "connect_shader_nodes", P(locals()), group="materials")

    @mcp.tool(name="set_shader_node_input")
    async def set_shader_node_input(
        material: str,
        node: str,
        inputs: dict[str, Any] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Set shader node input values / properties."""
        return await call_blender(ctx, "set_shader_node_input", P(locals()), group="materials")

    @mcp.tool(name="remove_shader_node")
    async def remove_shader_node(material: str, node: str) -> dict[str, Any]:
        """Delete a shader node."""
        return await call_blender(ctx, "remove_shader_node", P(locals()), group="materials")

    @mcp.tool(name="create_procedural_material")
    async def create_procedural_material(
        preset: MaterialPreset = "plastic",
        name: str | None = None,
        color: list[float] | None = None,
        roughness: float | None = None,
        texture_scale: float = 1.0,
        assign_to: list[str] | None = None,
        replace: bool = True,
        reuse: bool = True,
    ) -> dict[str, Any]:
        """Realistic PBR material from a preset ("make it polished chrome" -> chrome), with
        procedural texture/bump for wood, marble, brick, rust, fabric, concrete..."""
        return await call_blender(ctx, "create_procedural_material", P(locals()), group="materials")

    @mcp.tool(name="set_pbr_textures")
    async def set_pbr_textures(
        material: str,
        maps: dict[str, str],
        scale: float = 1.0,
        normal_strength: float = 1.0,
        displacement_scale: float = 0.05,
        emission_strength: float | None = None,
    ) -> dict[str, Any]:
        """Wire image maps {base_color, roughness, metallic, normal, displacement, alpha, emission,
        ao}
        with correct colour spaces, normal-map and displacement nodes."""
        return await call_blender_paths(
            ctx, "set_pbr_textures", P(locals()), group="materials", path_keys=("maps",)
        )

    @mcp.tool(name="set_material_surface")
    async def set_material_surface(
        material: str,
        base_color: list[float] | None = None,
        metallic: float | None = None,
        roughness: float | None = None,
        ior: float | None = None,
        alpha: float | None = None,
        transmission: float | None = None,
        emission_color: list[float] | None = None,
        emission_strength: float | None = None,
        procedural_bump: float | None = None,
        bump_scale: float | None = None,
    ) -> dict[str, Any]:
        """One-call PBR edits: metal, roughness, transparency, transmission, emission, bump."""
        return await call_blender(ctx, "set_material_surface", P(locals()), group="materials")
