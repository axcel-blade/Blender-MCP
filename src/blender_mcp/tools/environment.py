"""World, environment, architecture and whole-scene generator MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender, call_blender_paths
from blender_mcp.tools.registry import forward_params as P

Vegetation = Literal[
    "tree",
    "low_poly_tree",
    "dead_tree",
    "pine",
    "palm",
    "bush",
    "rock",
    "grass_tuft",
    "cactus",
    "mushroom",
]
Environment = Literal[
    "forest",
    "low_poly_forest",
    "pine_forest",
    "mountains",
    "desert",
    "ocean",
    "beach",
    "tropical_island",
    "winter",
    "alien_planet",
    "space",
    "fantasy",
    "swamp",
]


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="set_world_background")
    async def set_world_background(
        color: list[float] | None = None, strength: float = 1.0
    ) -> dict[str, Any]:
        """Solid world colour/strength (removes HDRI/sky links)."""
        return await call_blender(ctx, "set_world_background", P(locals()), group="environment")

    @mcp.tool(name="set_hdri_environment")
    async def set_hdri_environment(
        path: str,
        strength: float = 1.0,
        rotation: float = 0.0,
        hide_background: bool = False,
    ) -> dict[str, Any]:
        """Image-based lighting from an .hdr/.exr file (rotation in degrees). Poly Haven HDRIs
        are available through search_assets / import_external_asset."""
        return await call_blender_paths(
            ctx, "set_hdri_environment", P(locals()), group="environment"
        )

    @mcp.tool(name="set_sky")
    async def set_sky(
        sun_elevation: float = 15,
        sun_rotation: float = 0,
        strength: float = 1.0,
        sky_type: str | None = None,
        altitude: float | None = None,
        air_density: float | None = None,
        dust_density: float | None = None,
        ozone_density: float | None = None,
        add_sun: bool = True,
        sun_strength: float = 4.0,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Physical sky (degrees). Low elevation = sunrise/sunset. Adds a matching sun lamp."""
        return await call_blender(ctx, "set_sky", P(locals()), group="environment")

    @mcp.tool(name="add_atmosphere")
    async def add_atmosphere(
        mode: Literal["world", "box"] = "world",
        density: float = 0.02,
        color: list[float] | None = None,
        anisotropy: float = 0.2,
        size: float | None = None,
        location: list[float] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Volumetric fog/haze (world) or a local fog volume box for god rays."""
        return await call_blender(ctx, "add_atmosphere", P(locals()), group="environment")

    @mcp.tool(name="add_clouds")
    async def add_clouds(
        size: float = 200,
        thickness: float = 10,
        altitude: float = 60,
        coverage: float = 0.5,
        density: float = 2.0,
        scale: float = 3.0,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Volumetric cloud layer."""
        return await call_blender(ctx, "add_clouds", P(locals()), group="environment")

    @mcp.tool(name="set_weather")
    async def set_weather(
        weather: Literal[
            "clear", "sunset", "overcast", "foggy", "night", "storm", "snow", "rain"
        ] = "clear",
        area: float | None = None,
        height: float | None = None,
        intensity: int | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Weather mood: sky/world, fog, moonlight, and falling snow/rain particles."""
        return await call_blender(ctx, "set_weather", P(locals()), group="environment")

    @mcp.tool(name="create_terrain")
    async def create_terrain(
        style: Literal[
            "hills", "mountains", "dunes", "plateau", "canyon", "islands", "flat"
        ] = "hills",
        size: float = 100.0,
        resolution: int = 128,
        height: float = 10.0,
        noise_scale: float = 3.0,
        seed: int = 0,
        name: str | None = None,
        location: list[float] | None = None,
        palette: list[list[float]] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Procedural terrain mesh with a height-graded material (snowcaps, sand, grass...)."""
        return await call_blender(ctx, "create_terrain", P(locals()), group="environment")

    @mcp.tool(name="create_water")
    async def create_water(
        kind: Literal["ocean", "lake"] = "ocean",
        size: float = 100.0,
        level: float = 0.0,
        wave_scale: float = 1.5,
        wind: float = 15.0,
        choppiness: float = 1.2,
        resolution: int = 12,
        color: list[float] | None = None,
        name: str | None = None,
        location: list[float] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Realistic animated ocean (Ocean modifier + foam) or a still lake surface."""
        return await call_blender(ctx, "create_water", P(locals()), group="environment")

    @mcp.tool(name="scatter_objects")
    async def scatter_objects(
        surface: str,
        sources: list[str],
        count: int = 100,
        seed: int = 0,
        scale_range: list[float] | None = None,
        align_to_normal: bool = False,
        min_distance: float = 0.0,
        max_slope: float | None = None,
        min_height: float | None = None,
        max_height: float | None = None,
        hide_sources: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Scatter linked duplicates over a surface with slope/height/spacing rules (forests,
        rocks, crowds of props). For a live, non-destructive version use create_gn_scatter."""
        return await call_blender(ctx, "scatter_objects", P(locals()), group="environment")

    @mcp.tool(name="create_vegetation")
    async def create_vegetation(
        kind: Vegetation = "tree",
        height: float = 4.0,
        seed: int = 0,
        name: str | None = None,
        leaf_color: list[float] | None = None,
        location: list[float] | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Procedural plant/rock model (one joined object) - ideal scatter source."""
        return await call_blender(ctx, "create_vegetation", P(locals()), group="environment")

    @mcp.tool(name="generate_environment")
    async def generate_environment(
        preset: Environment = "forest",
        size: float = 120,
        seed: int = 0,
        density: float = 1.0,
        resolution: int | None = None,
        camera: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """One-call coherent environment: terrain, water, vegetation, sky/atmosphere and a framed
        camera, all in one collection. Refine afterwards with the individual tools."""
        return await call_blender(ctx, "generate_environment", P(locals()), group="environment")

    # ------------------------------------------------------------------ architecture

    @mcp.tool(name="create_room")
    async def create_room(
        width: float = 5,
        depth: float = 4,
        height: float = 2.7,
        wall_thickness: float = 0.2,
        windows: list[dict[str, Any]] | None = None,
        doors: list[dict[str, Any]] | None = None,
        ceiling: bool = True,
        light: bool = True,
        wall_color: list[float] | None = None,
        floor_color: list[float] | None = None,
        wall_material: str | None = None,
        floor_material: str | None = None,
        name: str | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Interior shell. Openings: {wall: north|south|east|west, offset, width, height, sill}."""
        return await call_blender(ctx, "create_room", P(locals()), group="environment")

    @mcp.tool(name="create_furniture")
    async def create_furniture(
        kind: Literal[
            "table", "chair", "sofa", "bed", "shelf", "desk", "lamp", "cabinet", "rug", "tv"
        ] = "table",
        location: list[float] | None = None,
        rotation: float = 0,
        color: list[float] | None = None,
        fabric_color: list[float] | None = None,
        name: str | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Real-world-scaled furniture piece."""
        return await call_blender(ctx, "create_furniture", P(locals()), group="environment")

    @mcp.tool(name="furnish_room")
    async def furnish_room(
        purpose: Literal["living_room", "bedroom", "office", "dining"] = "living_room",
        width: float = 5,
        depth: float = 4,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Lay out furniture for a room created by create_room (use the same width/depth)."""
        return await call_blender(ctx, "furnish_room", P(locals()), group="environment")

    @mcp.tool(name="create_building")
    async def create_building(
        floors: int = 3,
        width: float = 10,
        depth: float = 8,
        floor_height: float = 3.2,
        roof: Literal["flat", "gable"] = "flat",
        window_width: float = 1.2,
        window_spacing: float = 2.5,
        color: list[float] | None = None,
        material: str | None = None,
        location: list[float] | None = None,
        name: str | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Exterior building with window grid, floors and roof."""
        return await call_blender(ctx, "create_building", P(locals()), group="environment")

    @mcp.tool(name="create_stairs")
    async def create_stairs(
        steps: int = 12,
        width: float = 1.0,
        rise: float = 0.18,
        run: float = 0.28,
        spiral: bool = False,
        turn_per_step: float = 20,
        location: list[float] | None = None,
        name: str | None = None,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Straight or spiral staircase with code-like rise/run."""
        return await call_blender(ctx, "create_stairs", P(locals()), group="environment")

    @mcp.tool(name="create_castle")
    async def create_castle(
        size: float = 40,
        wall_height: float = 8,
        tower_radius: float = 3.5,
        camera: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Medieval castle: crenellated curtain walls, roofed towers, keep, gatehouse, courtyard."""
        return await call_blender(ctx, "create_castle", P(locals()), group="environment")

    @mcp.tool(name="create_city")
    async def create_city(
        blocks: int = 4,
        block_size: float = 30,
        road_width: float = 10,
        style: Literal["modern", "old_town", "sci_fi"] = "modern",
        seed: int = 0,
        camera: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Procedural city grid with varied buildings, roads, sidewalks and lit street lamps."""
        return await call_blender(ctx, "create_city", P(locals()), group="environment")

    @mcp.tool(name="create_village")
    async def create_village(
        houses: int = 10,
        radius: float = 40,
        trees: int = 80,
        seed: int = 0,
        camera: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Village of gable-roofed houses on terrain, surrounded by trees."""
        return await call_blender(ctx, "create_village", P(locals()), group="environment")

    @mcp.tool(name="create_product_shot")
    async def create_product_shot(
        target: str,
        lighting: str = "product",
        backdrop_color: list[float] | None = None,
        focal_length: float = 85,
        fstop: float = 4.0,
        turntable: bool = False,
        frames: int = 120,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Product visualisation: cyclorama backdrop, product lighting, DOF camera, optional
        turntable."""
        return await call_blender(ctx, "create_product_shot", P(locals()), group="environment")

    @mcp.tool(name="create_data_visualization")
    async def create_data_visualization(
        data: list[Any],
        kind: Literal["bar", "scatter", "surface", "line"] = "bar",
        height: float = 5.0,
        point_size: float = 0.1,
        thickness: float = 0.05,
        color: list[float] | None = None,
        axes: bool = True,
        axis_length: float = 10,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Scientific/infographic 3D charts: bar (list or 2D grid), scatter ([[x,y,z]]),
        surface (2D grid of z), line ([[x,y,z]])."""
        return await call_blender(
            ctx, "create_data_visualization", P(locals()), group="environment"
        )
