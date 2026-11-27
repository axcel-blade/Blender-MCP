# MCP Tools (overview)

## Blender app and files (core profile)

- **`open_blender(file_path="", version="", wait=True, list_installs_only=False, reopen_last=False)`** — starts Blender if the addon is not answering; does nothing if it already is, or while a Blender it launched is still starting.
  - `version` picks an install, e.g. `"5.3"` or `"5.2.1"`; the default is the newest. Versions come from the install folder name, or from `blender --version` (Steam installs).
  - `list_installs_only=True` lists every install found (path, version, source) without launching.
  - `wait=False` returns at once; `get_addon_status` reports `"blender": "starting"` until the addon answers.
  - `reopen_last=True` opens the file that was open when `close_blender` last quit Blender, for a quick restart (e.g. after reinstalling the addon). The server remembers it until it restarts.
  - `blender.path` / `BLENDER_MCP_BLENDER_PATH` overrides the search.
- **`close_blender(save=False, discard_changes=False)`** — quits Blender. Refuses on unsaved changes unless one of the flags is set. The reply names the file that was open, which `open_blender(reopen_last=True)` reopens.
- **`blend_file(action, path="", overwrite=False, discard_changes=False, recursive=False, keep_old=False)`** — manages the open `.blend` file:

| action | what it does |
|--------|--------------|
| `info` | Current path, and whether there are unsaved changes |
| `save` | Save in place, or to `path` |
| `save_as` | Save to `path` and keep working there; needs `overwrite` to replace a file |
| `save_copy` | Write a copy to `path`; keep working on the current file |
| `rename` | Rename the file on disk; `path` is a new name or a full path (`.blend` added if missing). Moves the old `.blend` and `.blend1` to the system trash (`keep_old=True` leaves them); refuses if the target exists |
| `open` | Open `path`; refuses on unsaved changes unless `discard_changes` |
| `new` | Start a new file; refuses on unsaved changes unless `discard_changes` |
| `revert` | Reload the last saved version, dropping unsaved changes |
| `list` | `.blend` files in `path` (default: the current file's folder); `recursive` includes subfolders |
| `recent` | Blender's File > Open Recent list, with missing files marked |
| `autosaves` | Autosave files and the last session (`quit.blend`) in Blender's temporary folder, newest first |
| `recover` | Open the autosave at `path`, or the last session when `path` is empty. The last session keeps its original path, so `save` writes over that file; an autosave points at the temporary folder, so keep it with `save_as`. The reply says where a save would go. Only files in Blender's temporary folder are accepted. Refuses on unsaved changes unless `discard_changes` |

## Tool groups (full profile)

Tool groups map to Blender addon handlers over the bridge.

- **Scene** — `get_scene_info`, `get_objects`, `diagnose_blender_connection`, …
- **Objects** — `create_cube`, `move_object`, `delete_object`, …
- **Meshes / Modifiers / Materials / Geometry Nodes**
- **Cameras / Lighting / Rendering / Animation**
- **Screenshots** — `get_viewport_screenshot`, `capture_multiple_angles`, …
- **Import/Export / Collections / Assets / Scripting**

### Production capability groups

| Group | Tools |
|---|---|
| `meshes` / `objects` / `scene` | `boolean_operation`, `loop_cut`, `bisect_mesh`, `bridge_edge_loops`, `dissolve_geometry`, `add_mesh_elements`, `spin_mesh`, `set_object_dimensions`, `set_scene_units`, `measure`, `array_along_curve` |
| `geometry_nodes` | `create_gn_scatter`, `create_parametric_object`, `remove_geometry_node` |
| `materials` | `add_shader_node`, `connect_shader_nodes`, `set_shader_node_input`, `remove_shader_node`, `create_procedural_material` (28 presets), `set_pbr_textures`, `set_material_surface` |
| `sculpting` | `set_sculpt_mode`, `set_sculpt_brush`, `sculpt_deform` (headless), `sculpt_stroke` (viewport), `sculpt_mask`, `sculpt_face_sets`, `set_dynamic_topology`, `voxel_remesh`, `add_multires` |
| `uv` | `uv_unwrap`, `mark_uv_seams`, `pack_uv_islands`, `get_uv_info` |
| `rigging` | `create_armature` (humanoid template), `add_bones`, `remove_bones`, `add_bone_constraint`, `add_object_constraint`, `setup_ik_chain`, `create_bone_controls`, `bind_mesh_to_armature`, `set_vertex_weights`, `normalize_vertex_weights`, `set_bone_pose`, `reset_pose`, `create_walk_cycle`, `validate_rig`, `test_rig_deformation`, `get_rig_info` |
| `animation` | `animate_property`, `set_keyframe_interpolation`, `make_animation_cyclic`, `add_fcurve_modifier`, `delete_keyframes`, `move_keyframes`, `list_fcurves`, `bake_animation`, `add_motion_path`, `follow_path`, `create_turntable`, `create_animated_text`, `import_motion_capture`, `retarget_animation` |
| `physics` | `add_rigid_body`, `add_soft_body`, `add_cloth`, `add_collision`, `add_fluid`, `quick_effect`, `add_particle_system`, `add_force_field`, `set_gravity`, `fracture_object`, `bake_simulation`, `free_simulation_cache`, `get_physics_info` |
| `rendering` | `configure_cycles`, `configure_eevee`, `configure_workbench`, `configure_render_passes`, `set_color_management`, `set_output_format`, `optimize_render_settings`, `batch_render` |
| `lighting` / `cameras` | `set_light_properties`, `create_studio_lighting`, `analyze_lighting`, `camera_track_object`, `create_camera_rig`, `set_camera_composition`, `create_camera_views` |
| `compositing` | `enable_compositor`, `add_compositor_node`, `connect_compositor_nodes`, `set_compositor_node`, `remove_compositor_node`, `apply_compositor_effect`, `composite_over_image`, `get_compositor_info` |
| `video_editing` | `vse_add_strip`, `vse_add_text`, `vse_add_transition`, `vse_add_effect`, `vse_edit_strip`, `vse_cut_strip`, `vse_remove_strip`, `vse_list_strips`, `vse_sync_audio`, `vse_render_video`, `load_movie_clip`, `track_camera_motion`, `get_tracking_info` |
| `grease_pencil` | `create_grease_pencil`, `draw_grease_pencil_stroke`, `draw_grease_pencil_shape`, `animate_grease_pencil`, `add_grease_pencil_modifier`, `get_grease_pencil_info` |
| `environment` | `set_world_background`, `set_hdri_environment`, `set_sky`, `add_atmosphere`, `add_clouds`, `set_weather`, `create_terrain`, `create_water`, `scatter_objects`, `create_vegetation`, `generate_environment`, `create_room`, `create_furniture`, `furnish_room`, `create_building`, `create_stairs`, `create_castle`, `create_city`, `create_village`, `create_product_shot`, `create_data_visualization` |
| `analysis` | `analyze_scene`, `analyze_mesh`, `find_missing_files`, `relink_missing_files`, `check_3d_print`, `prepare_for_3d_print`, `check_game_asset`, `prepare_game_asset` (plus `export_for_engine` in `import_export`) |
| `library` | `mark_as_asset`, `clear_asset`, `tag_asset`, `list_local_assets`, `list_asset_libraries`, `list_blend_contents`, `append_from_blend`, `manage_linked_libraries`, `pack_resources`, `purge_orphans` |
| `addons` | `list_addons`, `set_addon_enabled` |
| `safety` | `create_checkpoint`, `list_checkpoints`, `restore_checkpoint`, `undo`, `redo`, `get_undo_history`, `get_execution_history` |
| `automation` | `batch_apply`, `batch_rename`, `batch_export`, `run_workflow` |

Safety conventions:

- Destructive tools need `confirmed=true`: `remove_bones`, `vse_remove_strip`, `pack_resources(action="unpack")`, `purge_orphans`, `restore_checkpoint`, and `set_addon_enabled(enable=false)`. Ask the user before passing it.
- `prepare_for_3d_print` works on a copy by default. Exports refuse to overwrite a file unless `overwrite=true`.
- Every scene-changing command is its own undo step. `batch_apply` and `run_workflow` refuse to run code execution or file-replacing commands.
- `get_guide("workflows")` maps natural-language requests to these tools.

All tools return structured JSON with `success`, `result` / `error`, and `operation_id` when available.

## Visual verification (core profile)

- **`look(mode="viewport", view=None, camera=None, angles=None, max_size=768, samples=None)`** — returns images the model can see.

| mode | what it captures |
|------|------------------|
| `viewport` / `material` / `rendered` / `wireframe` | The 3D viewport with that shading (no compositor) |
| `camera` | The viewport through the active or named `camera`; the active camera is restored afterwards |
| `angles` | Several views in one call (`angles`, default FRONT, RIGHT, TOP, PERSPECTIVE) |
| `render` | A real render from the active or named `camera` with the compositor applied (glare, grading, volumes) |

`mode="render"` needs both the `screenshots` and `rendering` tool groups. It scales the render so its longest edge is at most `max_size` (and the configured `render.max_resolution_*`), caps `samples` (default: the scene's own) at `render.max_samples`, and allows `render.max_time_seconds` to finish (override with `bridge.command_timeouts.capture_render_view`). It restores camera, engine, samples, resolution percentage, compositing, output path and file format, even if the render fails, and never returns an image from an earlier render. With no camera it returns an error saying how to add one.

In the full profile, `get_viewport_screenshot`, `capture_camera_view` and the render tools are also available.

## Guides and prompts

`get_guide(name)` serves `bpy`, `materials`, `scene`, `workflows`, `realism` (photoreal checklist) and `cinematic` (stylised scenes from a reference). The `recreate_reference` prompt runs the staged cinematic workflow.
