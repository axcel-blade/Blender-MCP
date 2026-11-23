"""Rigging, weight painting, posing and advanced animation MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender, call_blender_paths
from blender_mcp.tools.registry import forward_params as P

Target = Literal["object", "data", "material", "world", "scene"]


def register(mcp: FastMCP, ctx: AppContext) -> None:

    @mcp.tool(name="create_armature")
    async def create_armature(
        name: str = "Armature",
        template: Literal["humanoid", "single", "custom"] = "custom",
        bones: list[dict[str, Any]] | None = None,
        height: float = 1.8,
        location: list[float] | None = None,
        display_type: Literal["OCTAHEDRAL", "STICK", "BBONE", "ENVELOPE", "WIRE"] = "OCTAHEDRAL",
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Create an armature. ``template='humanoid'`` builds a full biped (spine, arms, legs,
        .L/.R naming) scaled to ``height`` metres. Custom ``bones``: [{name, head, tail,
        parent?, connected?, roll?, deform?}] in armature-local coordinates."""
        return await call_blender(ctx, "create_armature", P(locals()), group="rigging")

    @mcp.tool(name="add_bones")
    async def add_bones(armature: str, bones: list[dict[str, Any]]) -> dict[str, Any]:
        """Add or edit bones ({name, head, tail, parent?, connected?, roll?, deform?})."""
        return await call_blender(ctx, "add_bones", P(locals()), group="rigging")

    @mcp.tool(name="remove_bones")
    async def remove_bones(
        armature: str, bones: list[str], confirmed: bool = False
    ) -> dict[str, Any]:
        """Delete bones (requires confirmed=true)."""
        return await call_blender(ctx, "remove_bones", P(locals()), group="rigging")

    @mcp.tool(name="add_bone_constraint")
    async def add_bone_constraint(
        armature: str,
        bone: str,
        constraint_type: str = "COPY_ROTATION",
        target: str | None = None,
        subtarget: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a pose-bone constraint (IK, COPY_ROTATION, DAMPED_TRACK, LIMIT_ROTATION, STRETCH_TO,
        ...)."""
        return await call_blender(ctx, "add_bone_constraint", P(locals()), group="rigging")

    @mcp.tool(name="add_object_constraint")
    async def add_object_constraint(
        name: str,
        constraint_type: str = "TRACK_TO",
        target: str | None = None,
        subtarget: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add an object constraint (TRACK_TO, CHILD_OF, FOLLOW_PATH, COPY_LOCATION, FLOOR, ...)."""
        return await call_blender(ctx, "add_object_constraint", P(locals()), group="rigging")

    @mcp.tool(name="setup_ik_chain")
    async def setup_ik_chain(
        armature: str,
        bone: str,
        chain_count: int = 2,
        pole: bool = True,
        pole_direction: float = 1.0,
        pole_angle: float | None = None,
    ) -> dict[str, Any]:
        """Create IK target (+pole) control bones for ``bone`` (e.g. shin.L, forearm.R) and wire IK.
        Bones without IK stay FK."""
        return await call_blender(ctx, "setup_ik_chain", P(locals()), group="rigging")

    @mcp.tool(name="create_bone_controls")
    async def create_bone_controls(
        armature: str,
        bones: list[str] | None = None,
        shape: Literal["CIRCLE", "CUBE", "SPHERE"] = "CIRCLE",
        scale: float = 1.0,
    ) -> dict[str, Any]:
        """Give pose bones custom-shape widgets so the rig has animator-friendly controls."""
        return await call_blender(ctx, "create_bone_controls", P(locals()), group="rigging")

    @mcp.tool(name="bind_mesh_to_armature")
    async def bind_mesh_to_armature(
        armature: str,
        meshes: list[str],
        mode: Literal["AUTO", "ENVELOPE", "EMPTY", "NONE"] = "AUTO",
    ) -> dict[str, Any]:
        """Skin meshes to an armature (AUTO = automatic weights). Reports unweighted vertices."""
        return await call_blender(ctx, "bind_mesh_to_armature", P(locals()), group="rigging")

    @mcp.tool(name="set_vertex_weights")
    async def set_vertex_weights(
        name: str,
        group: str,
        weight: float = 1.0,
        mode: Literal["REPLACE", "ADD", "SUBTRACT", "REMOVE"] = "REPLACE",
        vertex_indices: list[int] | None = None,
        center: list[float] | None = None,
        radius: float | None = None,
    ) -> dict[str, Any]:
        """Weight painting: set a vertex group's weights by indices, a world-space sphere, or all
        vertices."""
        return await call_blender(ctx, "set_vertex_weights", P(locals()), group="rigging")

    @mcp.tool(name="normalize_vertex_weights")
    async def normalize_vertex_weights(name: str) -> dict[str, Any]:
        """Normalise each vertex's unlocked group weights to sum to 1."""
        return await call_blender(ctx, "normalize_vertex_weights", P(locals()), group="rigging")

    @mcp.tool(name="set_bone_pose")
    async def set_bone_pose(
        armature: str, poses: list[dict[str, Any]], frame: int | None = None
    ) -> dict[str, Any]:
        """Pose bones: [{bone, rotation_euler?|rotation_quaternion?, location?, scale?, frame?}].
        With a frame, the pose is keyframed (pose-to-pose animation)."""
        return await call_blender(ctx, "set_bone_pose", P(locals()), group="rigging")

    @mcp.tool(name="reset_pose")
    async def reset_pose(armature: str) -> dict[str, Any]:
        """Return every pose bone to rest."""
        return await call_blender(ctx, "reset_pose", P(locals()), group="rigging")

    @mcp.tool(name="create_walk_cycle")
    async def create_walk_cycle(
        armature: str,
        frame_start: int = 1,
        cycle_frames: int = 24,
        stride_angle: float = 30.0,
    ) -> dict[str, Any]:
        """Keyframe a looping walk cycle on a humanoid-template rig."""
        return await call_blender(ctx, "create_walk_cycle", P(locals()), group="rigging")

    @mcp.tool(name="validate_rig")
    async def validate_rig(armature: str) -> dict[str, Any]:
        """Check roots, scale, zero-length bones, missing vertex groups, unweighted vertices, bad
        constraints."""
        return await call_blender(ctx, "validate_rig", P(locals()), group="rigging")

    @mcp.tool(name="test_rig_deformation")
    async def test_rig_deformation(armature: str) -> dict[str, Any]:
        """Wiggle each deform bone and report bones that move no skinned vertices."""
        return await call_blender(ctx, "test_rig_deformation", P(locals()), group="rigging")

    @mcp.tool(name="get_rig_info")
    async def get_rig_info(armature: str) -> dict[str, Any]:
        """Bone hierarchy, rest positions, deform flags and constraints."""
        return await call_blender(ctx, "get_rig_info", P(locals()), group="rigging")

    # ------------------------------------------------------------------ animation

    @mcp.tool(name="animate_property")
    async def animate_property(
        data_path: str,
        keyframes: list[dict[str, Any]],
        name: str | None = None,
        target: Target = "object",
        material: str | None = None,
        index: int = -1,
        interpolation: str | None = None,
        easing: str | None = None,
    ) -> dict[str, Any]:
        """Keyframe ANY animatable property: [{frame, value}]. Examples: object 'location' (index
        2),
        data 'energy' on a light, data 'lens' on a camera, material
        'nodes["Principled BSDF"].inputs[0].default_value', world/scene properties."""
        return await call_blender(ctx, "animate_property", P(locals()), group="animation")

    @mcp.tool(name="set_keyframe_interpolation")
    async def set_keyframe_interpolation(
        name: str | None = None,
        target: Target = "object",
        material: str | None = None,
        interpolation: Literal[
            "CONSTANT",
            "LINEAR",
            "BEZIER",
            "SINE",
            "QUAD",
            "CUBIC",
            "QUART",
            "QUINT",
            "EXPO",
            "CIRC",
            "BACK",
            "BOUNCE",
            "ELASTIC",
        ] = "BEZIER",
        easing: Literal["AUTO", "EASE_IN", "EASE_OUT", "EASE_IN_OUT"] | None = None,
        data_path: str | None = None,
        handle_type: str | None = None,
    ) -> dict[str, Any]:
        """Set interpolation/easing on all (or one data_path's) keyframes."""
        return await call_blender(ctx, "set_keyframe_interpolation", P(locals()), group="animation")

    @mcp.tool(name="make_animation_cyclic")
    async def make_animation_cyclic(
        name: str | None = None,
        target: Target = "object",
        material: str | None = None,
        data_path: str | None = None,
    ) -> dict[str, Any]:
        """Loop animation forever with a Cycles F-curve modifier."""
        return await call_blender(ctx, "make_animation_cyclic", P(locals()), group="animation")

    @mcp.tool(name="add_fcurve_modifier")
    async def add_fcurve_modifier(
        name: str | None = None,
        target: Target = "object",
        material: str | None = None,
        modifier_type: Literal[
            "NOISE", "CYCLES", "GENERATOR", "STEPPED", "LIMITS", "ENVELOPE"
        ] = "NOISE",
        data_path: str | None = None,
        index: int | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Procedural motion: NOISE (shake, flicker; settings scale/strength/phase), STEPPED (on-
        twos), ..."""
        return await call_blender(ctx, "add_fcurve_modifier", P(locals()), group="animation")

    @mcp.tool(name="delete_keyframes")
    async def delete_keyframes(
        name: str | None = None,
        target: Target = "object",
        material: str | None = None,
        data_path: str | None = None,
        frame_start: float | None = None,
        frame_end: float | None = None,
    ) -> dict[str, Any]:
        """Delete keyframes in a frame range (all when no range)."""
        return await call_blender(ctx, "delete_keyframes", P(locals()), group="animation")

    @mcp.tool(name="move_keyframes")
    async def move_keyframes(
        name: str | None = None,
        target: Target = "object",
        material: str | None = None,
        offset: float = 0.0,
        scale: float = 1.0,
        pivot: float = 0.0,
    ) -> dict[str, Any]:
        """Retime animation: shift by ``offset`` frames and/or stretch by ``scale`` around
        ``pivot``."""
        return await call_blender(ctx, "move_keyframes", P(locals()), group="animation")

    @mcp.tool(name="list_fcurves")
    async def list_fcurves(
        name: str | None = None, target: Target = "object", material: str | None = None
    ) -> Any:
        """List animated channels with key counts, ranges, interpolation and modifiers."""
        return await call_blender(ctx, "list_fcurves", P(locals()), group="animation")

    @mcp.tool(name="bake_animation")
    async def bake_animation(
        name: str,
        frame_start: int | None = None,
        frame_end: int | None = None,
        step: int = 1,
        visual_keying: bool = True,
        clear_constraints: bool = False,
        pose: bool = True,
    ) -> dict[str, Any]:
        """Bake constraints/drivers/IK/physics into plain keyframes (for export to engines)."""
        return await call_blender(ctx, "bake_animation", P(locals()), group="animation")

    @mcp.tool(name="add_motion_path")
    async def add_motion_path(
        name: str, frame_start: int | None = None, frame_end: int | None = None
    ) -> dict[str, Any]:
        """Calculate and display an object's motion path."""
        return await call_blender(ctx, "add_motion_path", P(locals()), group="animation")

    @mcp.tool(name="follow_path")
    async def follow_path(
        name: str,
        curve: str | None = None,
        radius: float = 5.0,
        center: list[float] | None = None,
        duration: int = 120,
        frame_start: int | None = None,
        follow_curve: bool = True,
        forward_axis: str | None = None,
        loop: bool = True,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Animate an object along a curve (a circular path is created when ``curve`` is
        omitted)."""
        return await call_blender(ctx, "follow_path", P(locals()), group="animation")

    @mcp.tool(name="create_turntable")
    async def create_turntable(
        target: str | None = None,
        camera: str | None = None,
        frames: int = 120,
        frame_start: int = 1,
        distance: float = 8.0,
        height: float = 2.0,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """360° camera orbit around a target (product spins, model showcases)."""
        return await call_blender(ctx, "create_turntable", P(locals()), group="animation")

    @mcp.tool(name="create_animated_text")
    async def create_animated_text(
        text: str,
        style: Literal["reveal", "spin", "scale_bounce", "fly_in"] = "reveal",
        name: str | None = None,
        size: float = 1.0,
        extrude: float = 0.1,
        bevel: float = 0.01,
        location: list[float] | None = None,
        material: str | None = None,
        frame_start: int = 1,
        duration: int = 40,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Motion graphics: extruded 3D title / animated logo text with an eased entrance."""
        return await call_blender(ctx, "create_animated_text", P(locals()), group="animation")

    @mcp.tool(name="import_motion_capture")
    async def import_motion_capture(
        path: str,
        scale: float = 1.0,
        frame_start: int = 1,
        use_fps_scale: bool = True,
        update_scene_fps: bool = False,
        update_scene_duration: bool = True,
    ) -> dict[str, Any]:
        """Import BVH/FBX motion capture as an animated armature."""
        return await call_blender_paths(
            ctx, "import_motion_capture", P(locals()), group="animation"
        )

    @mcp.tool(name="retarget_animation")
    async def retarget_animation(
        source: str,
        target: str,
        bone_map: dict[str, str] | None = None,
        root_bone: str | None = None,
        bake: bool = True,
        frame_start: int | None = None,
        frame_end: int | None = None,
    ) -> dict[str, Any]:
        """Retarget mocap from a source armature to a target rig ({source_bone: target_bone});
        matching names are mapped automatically. Baked to keyframes by default."""
        return await call_blender(ctx, "retarget_animation", P(locals()), group="animation")
