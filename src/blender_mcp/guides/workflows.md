# Production workflows

Work like a professional artist and technical director. Turn the request into a plan,
inspect before changing anything, build in named collections at real-world scale, check
with `look`, fix, and only then report back.

## The loop

1. **Understand** the goal, style, scale and deliverable (still, animation, asset, print).
   Ask only when something essential is missing (for example the output format of a print job).
2. **Inspect**: `get_scene_info`, `analyze_scene`. Respect `user_edits` and existing names.
3. **Protect**: `create_checkpoint` before destructive or large work. Every MCP command is
   its own undo step (`undo`, `redo`, `get_execution_history`).
4. **Build** in its own collection. Prefer one high-level generator, then refine it.
5. **Verify** with `look` (material or rendered mode for colour and light, several angles
   for proportion) and the QC tools (`analyze_mesh`, `check_3d_print`, `check_game_asset`,
   `validate_rig`, `analyze_lighting`).
6. **Optimise** with `optimize_render_settings`, decimating heavy meshes and instancing
   repeats (`scatter_objects`, `create_gn_scatter`).
7. **Deliver**: save, render or export (`blend_file`, `render_final`, `batch_render`,
   `export_for_engine`, `vse_render_video`), then report what was made and where it is.

For long plans, `run_workflow` runs a list of `{command, params}` steps in one call. It takes
a checkpoint first and reports each step.

## Mapping requests to tools

| Request | Starting tools |
|---|---|
| Medieval castle | `create_castle`, `generate_environment('mountains')`, `set_sky(sun_elevation=10)`, `create_camera_views` |
| Mountain village, cinematic | `create_village`, `set_weather('foggy' or 'sunset')`, `create_camera_rig('crane')`, `configure_cycles` |
| Low-poly forest | `generate_environment('low_poly_forest')`, `configure_eevee` |
| Procedural city | `create_city(style=...)`, `set_weather('night')` for lit streets |
| Realistic ocean | `create_water('ocean')`, `set_sky`, `add_clouds` |
| Realistic interior | `create_room(windows=...)`, `furnish_room`, `create_procedural_material('wood')`, `set_sky` for daylight through the windows |
| "Make it polished chrome" | `create_procedural_material('chrome', assign_to=[...])`, plus an HDRI (reflections need an environment) |
| Product advertisement | `create_product_shot(turntable=True)`, `apply_compositor_effect('bloom')`, `vse_add_text` |
| Rigged character that walks | model, then `create_armature(template='humanoid')`, `bind_mesh_to_armature`, `create_walk_cycle`, `validate_rig` |
| Destruction | `fracture_object(impact_point=...)`, `add_rigid_body(body_type='PASSIVE')` on the ground, a projectile with `add_rigid_body`, `bake_simulation` |
| Smoke and fire | `quick_effect('smoke_fire')` or `add_fluid` (DOMAIN, FLOW), then `bake_simulation(kind='fluid')` |
| Cloth or flag | `add_cloth(pin_group=...)`, `add_collision`, `add_force_field('WIND')` |
| Animated logo | `create_animated_text(style='scale_bounce')`, `create_studio_lighting('rim')`, `apply_compositor_effect('glare')` |
| Scene for Unreal or Unity | `prepare_game_asset(lod_ratios=[0.5, 0.25])`, `check_game_asset`, `export_for_engine('unreal')` |
| 3D printing | `check_3d_print`, then `prepare_for_3d_print(target_height_mm=...)` (works on a copy) |
| "Inspect my project" | `analyze_scene`, `find_missing_files`, `analyze_lighting`, `analyze_mesh` on the heavy objects |
| Improve the lighting | `analyze_lighting`, `create_studio_lighting`, `set_light_properties(temperature=...)`, `set_color_management(view_transform='AgX')` |
| Storyboard to animation | one `run_workflow` per shot: set, actors, `animate_property` and `set_bone_pose` keys, `create_camera_rig`, `vse_*` to cut the shots together |
| 2D animation | `create_grease_pencil`, `animate_grease_pencil`, `add_grease_pencil_modifier('BUILD')` |
| Data visualisation | `create_data_visualization(kind='surface' or 'bar')` |

Anything a tool does not cover is still possible with `execute_blender_code`. Use
`lookup_api` first to check names against the user's Blender version.

## Coherence rules

- One subject, a ground plane, deliberate lighting and a framed camera. Never leave
  disconnected objects floating in space.
- Use real scale: a door is 2.1 m, a chair seat 0.45 m, a storey about 3 m. Imported or
  generated assets arrive at arbitrary scale, so resize them and set them on the ground.
- Keep one material palette and reuse it, and put a light temperature or colour story
  behind every choice.
- Name everything (`SM_`, `Light_`, `Cam_`) and group related objects into collections.
