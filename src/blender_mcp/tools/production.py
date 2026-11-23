"""Quality control, asset libraries, add-ons, project safety, batch automation and motion
tracking."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from blender_mcp.tools.registry import AppContext, call_blender, call_blender_paths
from blender_mcp.tools.registry import forward_params as P

DataKind = Literal[
    "objects",
    "materials",
    "meshes",
    "collections",
    "node_groups",
    "worlds",
    "actions",
    "images",
    "brushes",
    "scenes",
]


def register(mcp: FastMCP, ctx: AppContext) -> None:

    # ------------------------------------------------------------------ analysis / QC

    @mcp.tool(name="analyze_scene")
    async def analyze_scene(
        heavy_threshold: int = 1_000_000, check_naming: bool = True
    ) -> dict[str, Any]:
        """Inspect the project and identify problems: stats, heavy meshes, missing materials/files,
        unapplied scale, broken modifiers, no camera/lights, orphans, organisation; health score."""
        return await call_blender(ctx, "analyze_scene", P(locals()), group="analysis")

    @mcp.tool(name="analyze_mesh")
    async def analyze_mesh(name: str) -> dict[str, Any]:
        """Topology report: tris/quads/ngons, non-manifold, loose, doubles, winding, volume."""
        return await call_blender(ctx, "analyze_mesh", P(locals()), group="analysis")

    @mcp.tool(name="find_missing_files")
    async def find_missing_files() -> dict[str, Any]:
        """List missing images, libraries, sounds, clips and fonts."""
        return await call_blender(ctx, "find_missing_files", {}, group="analysis")

    @mcp.tool(name="relink_missing_files")
    async def relink_missing_files(search_dir: str) -> dict[str, Any]:
        """Find missing files by name under ``search_dir`` and relink them."""
        return await call_blender_paths(
            ctx, "relink_missing_files", P(locals()), group="analysis", path_keys=("search_dir",)
        )

    @mcp.tool(name="check_3d_print")
    async def check_3d_print(
        name: str,
        min_thickness_mm: float = 0.8,
        build_volume_mm: list[float] | None = None,
    ) -> dict[str, Any]:
        """3D-print readiness: watertight, normals, self-intersections, thin walls, overhangs,
        size, volume."""
        return await call_blender(ctx, "check_3d_print", P(locals()), group="analysis")

    @mcp.tool(name="prepare_for_3d_print")
    async def prepare_for_3d_print(
        name: str,
        duplicate: bool = True,
        apply_modifiers: bool = True,
        merge_distance: float | None = None,
        triangulate: bool = False,
        voxel_remesh: float | None = None,
        set_millimetres: bool = True,
        target_height_mm: float | None = None,
        min_thickness_mm: float | None = None,
    ) -> dict[str, Any]:
        """Optimise for printing (on a copy by default): apply, merge, fill holes, fix normals,
        optional voxel remesh, scale to target size, drop onto the build plate, then re-check."""
        return await call_blender(ctx, "prepare_for_3d_print", P(locals()), group="analysis")

    @mcp.tool(name="check_game_asset")
    async def check_game_asset(
        name: str,
        triangle_budget: int = 10000,
        max_materials: int = 4,
        needs_lightmap: bool = False,
    ) -> dict[str, Any]:
        """Game-readiness: triangle budget, UVs, lightmap UV, transforms, ngons, material count,
        naming, origin."""
        return await call_blender(ctx, "check_game_asset", P(locals()), group="analysis")

    @mcp.tool(name="prepare_game_asset")
    async def prepare_game_asset(
        name: str,
        lightmap_uv: bool = True,
        triangulate: bool = True,
        rename: bool = True,
        lod_ratios: list[float] | None = None,
        triangle_budget: int | None = None,
    ) -> dict[str, Any]:
        """Apply transforms, origin to base, UVs + lightmap UV, triangulate, SM_ naming, LODs (e.g.
        [0.5, 0.25])."""
        return await call_blender(ctx, "prepare_game_asset", P(locals()), group="analysis")

    @mcp.tool(name="export_for_engine")
    async def export_for_engine(
        path: str,
        engine: Literal["unreal", "unity", "godot", "gltf", "web"] = "unreal",
        objects: list[str] | None = None,
        animation: bool = True,
        binary: bool = True,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Export with engine-correct scale/axes (Unreal/Unity FBX, Godot/web glTF)."""
        return await call_blender_paths(
            ctx, "export_for_engine", P(locals()), group="import_export", must_exist=False
        )

    # ------------------------------------------------------------------ asset library

    @mcp.tool(name="mark_as_asset")
    async def mark_as_asset(
        names: list[str],
        kind: DataKind = "objects",
        tags: list[str] | None = None,
        description: str | None = None,
        author: str | None = None,
        catalog_id: str | None = None,
    ) -> dict[str, Any]:
        """Mark data-blocks as Asset Browser assets with tags/description/preview."""
        return await call_blender(ctx, "mark_as_asset", P(locals()), group="library")

    @mcp.tool(name="clear_asset")
    async def clear_asset(names: list[str], kind: DataKind = "objects") -> dict[str, Any]:
        """Unmark assets."""
        return await call_blender(ctx, "clear_asset", P(locals()), group="library")

    @mcp.tool(name="tag_asset")
    async def tag_asset(
        name: str,
        kind: DataKind = "objects",
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add/remove asset tags."""
        return await call_blender(ctx, "tag_asset", P(locals()), group="library")

    @mcp.tool(name="list_local_assets")
    async def list_local_assets(query: str | None = None) -> Any:
        """Search assets marked in this file by name, tag or description."""
        return await call_blender(ctx, "list_local_assets", P(locals()), group="library")

    @mcp.tool(name="list_asset_libraries")
    async def list_asset_libraries() -> Any:
        """Asset libraries configured in Blender preferences."""
        return await call_blender(ctx, "list_asset_libraries", {}, group="library")

    @mcp.tool(name="list_blend_contents")
    async def list_blend_contents(
        path: str,
        kinds: list[str] | None = None,
        assets_only: bool = False,
    ) -> dict[str, Any]:
        """List objects/collections/materials/node groups inside another .blend file."""
        return await call_blender_paths(ctx, "list_blend_contents", P(locals()), group="library")

    @mcp.tool(name="append_from_blend")
    async def append_from_blend(
        path: str,
        kind: DataKind = "objects",
        names: list[str] | None = None,
        link: bool = False,
        instance: bool = False,
        collection: str | None = None,
    ) -> dict[str, Any]:
        """Reuse assets: append (copy) or link (live reference) data from another .blend."""
        return await call_blender_paths(ctx, "append_from_blend", P(locals()), group="library")

    @mcp.tool(name="manage_linked_libraries")
    async def manage_linked_libraries(
        action: Literal["list", "reload", "make_local"] = "list",
        name: str | None = None,
    ) -> Any:
        """List/reload linked libraries or make a linked object local."""
        return await call_blender(ctx, "manage_linked_libraries", P(locals()), group="library")

    @mcp.tool(name="pack_resources")
    async def pack_resources(
        action: Literal["pack", "unpack", "make_relative", "make_absolute"] = "pack",
        method: Literal["USE_LOCAL", "WRITE_LOCAL", "USE_ORIGINAL", "WRITE_ORIGINAL"] | None = None,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Pack external files into the .blend, unpack them (confirmed), or fix path styles."""
        return await call_blender(ctx, "pack_resources", P(locals()), group="library")

    @mcp.tool(name="purge_orphans")
    async def purge_orphans(confirmed: bool = False) -> dict[str, Any]:
        """Preview, then (confirmed=true) delete unused data-blocks."""
        return await call_blender(ctx, "purge_orphans", P(locals()), group="library")

    # ------------------------------------------------------------------ add-ons

    @mcp.tool(name="list_addons")
    async def list_addons(enabled_only: bool = False, query: str | None = None) -> Any:
        """Installed add-ons/extensions with enabled state."""
        return await call_blender(ctx, "list_addons", P(locals()), group="addons")

    @mcp.tool(name="set_addon_enabled")
    async def set_addon_enabled(
        module: str,
        enable: bool = True,
        confirmed: bool = False,
        save_preferences: bool = False,
    ) -> dict[str, Any]:
        """Enable an add-on, or disable one (confirmed=true). Persists only with
        save_preferences."""
        return await call_blender(ctx, "set_addon_enabled", P(locals()), group="addons")

    # ------------------------------------------------------------------ safety

    @mcp.tool(name="create_checkpoint")
    async def create_checkpoint(label: str = "checkpoint", keep: int = 20) -> dict[str, Any]:
        """Save a timestamped backup copy (.mcp_checkpoints next to the file) before risky work."""
        return await call_blender(ctx, "create_checkpoint", P(locals()), group="safety")

    @mcp.tool(name="list_checkpoints")
    async def list_checkpoints() -> Any:
        """Checkpoints for the current project, newest first."""
        return await call_blender(ctx, "list_checkpoints", {}, group="safety")

    @mcp.tool(name="restore_checkpoint")
    async def restore_checkpoint(
        path: str, confirmed: bool = False, save_over_original: bool = False
    ) -> dict[str, Any]:
        """Open a checkpoint (discards unsaved changes: ask the user first, then confirmed=true)."""
        return await call_blender(ctx, "restore_checkpoint", P(locals()), group="safety")

    @mcp.tool(name="undo")
    async def undo(steps: int = 1) -> dict[str, Any]:
        """Undo the last steps (each MCP command is its own undo step)."""
        return await call_blender(ctx, "undo", P(locals()), group="safety")

    @mcp.tool(name="redo")
    async def redo(steps: int = 1) -> dict[str, Any]:
        """Redo undone steps."""
        return await call_blender(ctx, "redo", P(locals()), group="safety")

    @mcp.tool(name="get_undo_history")
    async def get_undo_history(limit: int = 30) -> dict[str, Any]:
        """Blender's undo stack names."""
        return await call_blender(ctx, "get_undo_history", P(locals()), group="safety")

    @mcp.tool(name="get_execution_history")
    async def get_execution_history(limit: int = 50, failures_only: bool = False) -> dict[str, Any]:
        """Log of commands run in Blender this session: params, success, errors, timing."""
        return await call_blender(ctx, "get_execution_history", P(locals()), group="safety")

    # ------------------------------------------------------------------ automation

    @mcp.tool(name="batch_apply")
    async def batch_apply(
        command: str,
        params: dict[str, Any] | None = None,
        objects: list[str] | None = None,
        pattern: str | None = None,
        object_type: str | None = None,
        collection: str | None = None,
        name_param: str = "name",
        stop_on_error: bool = False,
    ) -> dict[str, Any]:
        """Run any command on many objects (by list, glob pattern, type or collection), e.g.
        command='create_procedural_material' with params={'preset': 'chrome'} and
        name_param='assign_to'... Code execution is not batchable."""
        return await call_blender(ctx, "batch_apply", P(locals()), group="automation")

    @mcp.tool(name="batch_rename")
    async def batch_rename(
        objects: list[str] | None = None,
        pattern: str | None = None,
        object_type: str | None = None,
        collection: str | None = None,
        find: str | None = None,
        replace: str | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
        numbered_base: str | None = None,
        rename_data: bool = False,
    ) -> dict[str, Any]:
        """Rename many objects: find/replace, prefix/suffix, or numbered (Base_001...)."""
        return await call_blender(ctx, "batch_rename", P(locals()), group="automation")

    @mcp.tool(name="batch_export")
    async def batch_export(
        directory: str,
        format: Literal["glb", "gltf", "fbx", "obj", "stl", "usd"] = "glb",
        objects: list[str] | None = None,
        pattern: str | None = None,
        object_type: str | None = None,
        collection: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Export each matching object to its own file."""
        return await call_blender_paths(
            ctx,
            "batch_export",
            P(locals()),
            group="automation",
            path_keys=("directory",),
            must_exist=False,
        )

    @mcp.tool(name="run_workflow")
    async def run_workflow(
        steps: list[dict[str, Any]],
        checkpoint: bool = True,
        stop_on_error: bool = True,
        verbose: bool = False,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Run a multi-step production plan in one call: [{command, params, label?}] using any
        tool's command name (e.g. a storyboard: build set, light, animate camera, render).
        Takes a checkpoint first and reports every step."""
        return await call_blender(ctx, "run_workflow", P(locals()), group="automation")

    # ------------------------------------------------------------------ motion tracking

    @mcp.tool(name="load_movie_clip")
    async def load_movie_clip(
        path: str,
        set_scene_range: bool = True,
        sensor_width: float | None = None,
        focal_length: float | None = None,
    ) -> dict[str, Any]:
        """Load footage for motion tracking."""
        return await call_blender_paths(ctx, "load_movie_clip", P(locals()), group="video_editing")

    @mcp.tool(name="track_camera_motion")
    async def track_camera_motion(
        clip: str,
        threshold: float = 0.3,
        min_distance: int = 120,
        setup_scene: bool = True,
    ) -> dict[str, Any]:
        """Detect + track features, solve camera motion and build a matching 3D scene (needs the
        UI)."""
        return await call_blender(ctx, "track_camera_motion", P(locals()), group="video_editing")

    @mcp.tool(name="get_tracking_info")
    async def get_tracking_info(clip: str) -> dict[str, Any]:
        """Tracks, solve status/error and tracking camera settings."""
        return await call_blender(ctx, "get_tracking_info", P(locals()), group="video_editing")
