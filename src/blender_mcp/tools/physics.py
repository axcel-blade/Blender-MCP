"""Physics, simulation and destruction MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender
from blender_mcp.tools.registry import forward_params as P


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="add_rigid_body")
    async def add_rigid_body(
        name: str | None = None,
        names: list[str] | None = None,
        body_type: Literal["ACTIVE", "PASSIVE"] = "ACTIVE",
        mass: float = 1.0,
        friction: float = 0.5,
        bounciness: float = 0.0,
        shape: Literal[
            "CONVEX_HULL", "MESH", "BOX", "SPHERE", "CAPSULE", "CYLINDER", "CONE", "COMPOUND"
        ] = "CONVEX_HULL",
        animated: bool | None = None,
        frame_end: int | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Rigid body physics. PASSIVE for floors/static colliders; creates the rigid body world."""
        return await call_blender(ctx, "add_rigid_body", P(locals()), group="physics")

    @mcp.tool(name="add_soft_body")
    async def add_soft_body(
        name: str,
        mass: float = 1.0,
        stiffness: float = 0.5,
        use_goal: bool = False,
        goal_strength: float = 0.7,
        self_collision: bool = False,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Soft body (jelly, cushions, wobble)."""
        return await call_blender(ctx, "add_soft_body", P(locals()), group="physics")

    @mcp.tool(name="add_cloth")
    async def add_cloth(
        name: str,
        preset: Literal["cotton", "silk", "denim", "leather", "rubber"] = "cotton",
        self_collision: bool = True,
        pin_group: str | None = None,
        pressure: float | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Cloth simulation with fabric presets; ``pin_group`` pins a vertex group (curtains,
        flags);
        ``pressure`` inflates closed meshes (balloons, cushions). Add colliders with
        add_collision."""
        return await call_blender(ctx, "add_cloth", P(locals()), group="physics")

    @mcp.tool(name="add_collision")
    async def add_collision(
        name: str | None = None,
        names: list[str] | None = None,
        thickness: float = 0.02,
        friction: float = 5.0,
        damping: float = 0.1,
    ) -> dict[str, Any]:
        """Make objects collide with cloth, soft bodies and particles."""
        return await call_blender(ctx, "add_collision", P(locals()), group="physics")

    @mcp.tool(name="add_fluid")
    async def add_fluid(
        name: str,
        role: Literal["DOMAIN", "FLOW", "EFFECTOR"] = "DOMAIN",
        domain_type: Literal["GAS", "LIQUID"] = "GAS",
        resolution: int = 64,
        flow_type: Literal["SMOKE", "FIRE", "BOTH", "LIQUID"] = "SMOKE",
        flow_behavior: Literal["INFLOW", "OUTFLOW", "GEOMETRY"] = "INFLOW",
        flow_source: Literal["MESH", "PARTICLES"] = "MESH",
        effector_type: Literal["COLLISION", "GUIDE"] = "COLLISION",
        frame_end: int = 250,
        cache_dir: str | None = None,
        high_res_noise: bool = False,
        dissolve: bool = False,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mantaflow fluids: a DOMAIN (GAS = smoke/fire, LIQUID = water) plus FLOW emitters and
        EFFECTOR obstacles. Bake with bake_simulation(kind='fluid', name=domain)."""
        return await call_blender(ctx, "add_fluid", P(locals()), group="physics")

    @mcp.tool(name="quick_effect")
    async def quick_effect(
        effect: Literal["smoke", "fire", "smoke_fire", "liquid", "explode", "fur"],
        name: str | None = None,
        names: list[str] | None = None,
        pieces: int = 100,
        frame_start: int = 1,
        frame_end: int = 10,
        density: Literal["LIGHT", "MEDIUM", "HEAVY"] = "MEDIUM",
    ) -> dict[str, Any]:
        """Blender Quick Effects: smoke, fire, liquid, explode or fur on objects."""
        return await call_blender(ctx, "quick_effect", P(locals()), group="physics")

    @mcp.tool(name="add_particle_system")
    async def add_particle_system(
        name: str,
        particle_type: Literal["EMITTER", "HAIR"] = "EMITTER",
        count: int = 1000,
        system_name: str | None = None,
        seed: int = 0,
        frame_start: float = 1,
        frame_end: float = 200,
        lifetime: float = 50,
        velocity: float = 1.0,
        random_velocity: float = 0.0,
        gravity: float | None = None,
        hair_length: float = 0.2,
        segments: int = 5,
        children: int | None = None,
        randomness: float = 0.0,
        instance_object: str | None = None,
        instance_collection: str | None = None,
        size: float = 0.1,
        size_random: float = 0.0,
        random_rotation: float = 0.0,
        density_group: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Particles (sparks, debris, snow) or HAIR (hair, fur, grass). Instance objects/collections
        for scattering; ``density_group`` limits emission to a vertex group."""
        return await call_blender(ctx, "add_particle_system", P(locals()), group="physics")

    @mcp.tool(name="add_force_field")
    async def add_force_field(
        field_type: Literal[
            "WIND",
            "FORCE",
            "VORTEX",
            "TURBULENCE",
            "HARMONIC",
            "MAGNET",
            "DRAG",
            "CHARGE",
            "LENNARDJ",
            "BOID",
            "CURVE_GUIDE",
            "FLUID_FLOW",
        ] = "WIND",
        name: str | None = None,
        strength: float = 5.0,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
        flow: float | None = None,
        noise: float | None = None,
        falloff: str | None = None,
        collection: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Force field empty (wind, vortex, turbulence, ...) affecting particles, cloth, smoke,
        rigid bodies."""
        return await call_blender(ctx, "add_force_field", P(locals()), group="physics")

    @mcp.tool(name="set_gravity")
    async def set_gravity(
        enabled: bool = True, gravity: list[float] | None = None
    ) -> dict[str, Any]:
        """Scene gravity vector (default [0, 0, -9.81]) and on/off."""
        return await call_blender(ctx, "set_gravity", P(locals()), group="physics")

    @mcp.tool(name="fracture_object")
    async def fracture_object(
        name: str,
        pieces: int = 12,
        seed: int = 0,
        impact_point: list[float] | None = None,
        rigid_body: bool = True,
        chunk_mass: float = 0.5,
        hide_original: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Destruction: Voronoi-fracture a mesh into chunks (denser near ``impact_point``), as
        active rigid bodies ready to fall/shatter. Pair with a PASSIVE floor and a projectile."""
        return await call_blender(ctx, "fracture_object", P(locals()), group="physics")

    @mcp.tool(name="bake_simulation")
    async def bake_simulation(
        kind: Literal["all", "rigid_body", "fluid", "geometry_nodes"] = "all",
        name: str | None = None,
        frame_start: int | None = None,
        frame_end: int | None = None,
    ) -> dict[str, Any]:
        """Bake simulation caches (``name`` = fluid domain for kind='fluid'). Can take a long
        time."""
        return await call_blender(ctx, "bake_simulation", P(locals()), group="physics")

    @mcp.tool(name="free_simulation_cache")
    async def free_simulation_cache(name: str | None = None) -> dict[str, Any]:
        """Free baked caches (one fluid domain, or all point caches)."""
        return await call_blender(ctx, "free_simulation_cache", P(locals()), group="physics")

    @mcp.tool(name="get_physics_info")
    async def get_physics_info(name: str | None = None) -> dict[str, Any]:
        """Rigid bodies, cloth/soft/fluid/particle systems, force fields, gravity and bake state."""
        return await call_blender(ctx, "get_physics_info", P(locals()), group="physics")
