# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `look(mode="render")`: a real render from the active or named camera with the compositor applied, so glare, colour grading, fog and volumes can be checked visually from the core profile. It honours `max_size`, the render sample/resolution limits, the `screenshots` and `rendering` tool groups and `render.max_time_seconds` (or `command_timeouts.capture_render_view`) as the client and addon timeout, restores every setting it changes, and errors clearly when there is no camera or the render fails.
- `get_guide("cinematic")`: stylised and concept-art scenes from a reference image: matching the camera, Bezier tracks and bridges, displaced cliffs and floating islands, storm skies, volumetric fog, lightning, emissive and wet materials, rain, compositor glare and grading, with notes on API differences between Blender 3.6, 4.x and 5.x.
- `recreate_reference` prompt: a six-stage workflow (blockout, main structures, detail, materials, sky and lighting, compositing) that renders, compares with the reference, fixes the three biggest differences and waits for feedback after each stage.

### Changed

- Server instructions send stylised/cinematic requests to the cinematic guide and its staged workflow; photoreal requests still go to the realism guide.

### Fixed

- Render handlers could return an image left over from an earlier render (for example with `write_still=False`, or when the render wrote nothing). They now return only this render's image, or an error.
- Render handlers now restore the output path, samples, engine, resolution percentage and file format afterwards, even when the render fails.
- `capture_camera_view` with a `camera` no longer leaves that camera as the scene's active camera.

## [1.7.0] - 2026-11-25

### Added

- `get_guide("realism")`: a checklist for photoreal results covering real assets, beveled geometry, PBR materials at real-world scale, HDRI and area lighting, Cycles and AgX, a real-lens camera, environments and landscapes (slope-blended terrain, boulders, scattered vegetation), and pitfalls seen in real builds.
- `create_realistic_scene` prompt for photoreal scenes.

### Changed

- The server instructions tell the AI to read the realism guide whenever a request asks for something realistic, and never to deliver plain primitives with flat colors.
- `create_product_model` and `create_environment` prompts follow the realism guide; `create_environment` aims for realism unless a stylized look is requested.

### Fixed

- MCP prompts contained a literal `\n` instead of line breaks.

## [1.6.0] - 2026-11-23

### Added

- Full-profile tool coverage for complete production work: about 170 new tools, with matching addon commands, in eight new modules.
  - **Sculpting & UV**: brush selection, headless brush-style `sculpt_deform` (draw, clay, inflate, smooth, grab, snake hook, crease, flatten, scrape, pinch), real viewport strokes, masks, face sets, Dyntopo, voxel remesh, Multires; `uv_unwrap` (smart, angle-based, cube, cylinder, sphere, lightmap), seams, packing and UV diagnostics.
  - **Rigging & animation**: armatures with a humanoid template, bones, bone and object constraints, IK/FK with poles, control widgets, automatic skinning, weight painting, posing, walk cycles, `validate_rig` and `test_rig_deformation`. Keyframes on any property (including materials, lights and cameras), interpolation, loops, F-curve modifiers, retiming, baking, motion paths, follow-path, turntables, animated 3D text, BVH/FBX motion capture import and retargeting.
  - **Physics**: rigid bodies, soft bodies, cloth presets, collisions, Mantaflow fluids, smoke and fire, quick effects, particles and hair, force fields, gravity, Voronoi `fracture_object` for destruction, baking and cache management.
  - **Rendering, lighting & cameras**: Cycles (with GPU backend selection), EEVEE and Workbench setup, render passes, colour management, image and video output formats, quality profiles, `batch_render` per camera; light colour temperature, size and shadows, studio and cinematic light rigs, `analyze_lighting`; camera tracking, orbit, dolly, crane and handheld rigs, composition guides, multi-view cameras.
  - **Compositing, video editing & 2D**: compositor nodes and one-call effects (glare/bloom, blur, colour grade, vignette, denoise, lens distortion, sharpen, exposure), alpha-over; VSE movie, sound, image, colour and text strips, transitions, effects, cut, trim, fades, audio sync and video render; Grease Pencil drawing, shapes, frame-by-frame animation and modifiers (GPv2 and GPv3).
  - **Environments & architecture**: world colour, HDRI, physical sky, fog and volumes, clouds and weather; procedural terrain, ocean and lakes, vegetation, surface scattering; rooms with openings, furniture, buildings, stairs, castles, cities and villages; `generate_environment` presets (forest, mountains, desert, ocean, island, winter, alien planet, space, ...), product studio shots and 3D data visualisation.
  - **Modeling & materials**: booleans, loop cuts, bisect/knife, bridging, dissolve, raw geometry, spin/lathe, exact dimensions, scene units, measurement, array-along-curve; Geometry Nodes scattering and parametric objects; shader-node editing, 28 procedural PBR material presets and PBR texture-map wiring.
  - **Production**: `analyze_scene` project audit with a health score, mesh topology analysis, missing-file detection and relinking, 3D-print checks and fixes, game-asset checks, prep with LODs, and engine-specific export (Unreal, Unity, Godot, web); Asset Browser marking and tags, append and link from `.blend` files, pack/unpack, orphan purge; add-on listing and toggling; checkpoints, undo/redo, execution history; `batch_apply`, `batch_rename`, `batch_export` and `run_workflow` for multi-step plans; motion tracking (load clip, track, solve camera).
- `get_guide("workflows")`: maps creative requests to tool sequences and production rules.
- New tool groups: `sculpting`, `uv`, `rigging`, `physics`, `compositing`, `video_editing`, `grease_pencil`, `environment`, `analysis`, `library`, `safety`, `automation`, `addons`.
- Tools that read or write files check their paths against `security.allowed_directories`.
- Longer default timeouts for bakes, batch renders, workflows and scene generators.

### Changed

- Each successful addon command that changes the scene pushes its own undo step (`MCP: <command>`). The addon keeps a log of the last 500 commands for `get_execution_history`.
- The core profile is unchanged. All new tools are in the full profile only.

### Fixed

- Objects created into a named collection could end up invisible: when a collection with that name already existed only in another scene, it was reused without being linked into the active scene. Tools now use (or create, e.g. `Castle.001`) a collection that belongs to the active scene, and never pull in another scene's contents.
- `sculpt_stroke` failed on Blender 5.x because stroke elements no longer accept `pen_flip`. Stroke keys are now matched to the running Blender's API.
- `get_undo_history` returned an empty list on Blender 5.x. It now reads `WindowManager.undo_stack`.

## [1.5.0] - 2026-11-21

### Added

- `open_blender` (core tool): launches Blender when the addon bridge is not answering, optionally opening a `.blend` file, and waits until the bridge accepts connections. It looks for Blender in `BLENDER_MCP_BLENDER_PATH`, then `PATH`, then the usual install folders (Program Files, Microsoft Store and Steam on Windows, `/Applications` on macOS, `/usr/bin` and `/snap/bin` on Linux).
- `close_blender` (core tool): quits Blender. It refuses when the file has unsaved changes unless `save=True` or `discard_changes=True`. If the addon is not answering, it can only terminate a Blender that the server itself started.
- `blend_file` (core tool): one tool for the open `.blend` file, with actions `info`, `save`, `save_as`, `save_copy`, `rename`, `open`, `new`, `revert` and `list`. `rename` renames the file on disk. `open` and `new` refuse to drop unsaved changes unless `discard_changes=True`. Paths follow `security.allowed_directories`.
- `blend_file` actions `recent` (Blender's Open Recent list), `autosaves` (autosaves and the last session, `quit.blend`) and `recover` (open an autosave or the last session; the reply says where a plain save would write). `recover` only accepts files from Blender's temporary folder.
- `open_blender(reopen_last=True)` reopens the file that was open when `close_blender` last quit Blender, so restarting Blender keeps your place. `close_blender` replies with that file.
- New addon commands: `quit_blender`, `blend_file_info`, `save_copy`, `rename_blend_file`, `new_blend_file`, `revert_blend_file`, `list_blend_files`, `recent_blend_files`, `list_autosaves`, `recover_blend_file`.
- Settings `[blender] path` and `launch_timeout` in `config.toml` (env: `BLENDER_MCP_BLENDER_PATH`, `BLENDER_MCP_BLENDER_LAUNCH_TIMEOUT`; timeout default 60 seconds).

### Changed

- The core profile now has 16 tools.
- CI now lints and format-checks `blender_addon/` and `scripts/` as well as `src/` and `tests/`. Existing lint errors there are fixed (layout only, apart from equivalent rewrites such as `contextlib.suppress` and `TimeoutError`).
- `blend_file rename` moves the old `.blend` and `.blend1` to the system trash (Recycle Bin, macOS Trash, freedesktop Trash) instead of deleting them. If that fails, the old file is left in place and the reply says so. `keep_old=True` keeps it.
- `open_blender` picks the newest installed version by default instead of the first one found, and takes `version` (e.g. `"5.3"`) to choose one. `list_installs_only=True` lists the installs without launching.
- While a Blender launched by `open_blender` is still loading, `get_addon_status` reports `"blender": "starting"` and `open_blender` does not start a second one.
- `get_addon_status` warns when the installed addon lacks the new file commands (`quit_blender`, `blend_file_info`, `rename_blend_file`, `save_copy`, `recent_blend_files`, `recover_blend_file`).

### Fixed

- Unsaved-change checks now see edits made through the bridge. Blender's `bpy.data.is_dirty` ignores changes made from scripts, so the addon now also tracks scene changes itself.
- Environment variables (and `.env`) now override `config.toml`, as the loader always claimed. Before, any `config.toml` replaced every environment setting, including ones the file did not mention: a file without a `[security]` section reset `script_permission` to `restricted` despite `BLENDER_MCP_SCRIPT_PERMISSION`.
- Only `BLENDER_MCP_*` environment variables are read. Before, unprefixed names also worked (`PORT`, `HOST`, `LOG_LEVEL`, `AUTH_TOKEN`, `SAFE_EXECUTION`, the API keys and so on), so a `PORT` set by another tool could silently move the bridge to a different port. If you relied on an unprefixed name, add the `BLENDER_MCP_` prefix.
- `blend_file rename` with a bare name now checks the final path (next to the open file) against `security.allowed_directories` before renaming.

Reinstall the addon (`blender-mcp install-addon`) to use `close_blender` and `blend_file`.

## [1.4.0] - 2026-11-20

### Added

- `lookup_api` (core tool): looks up the Blender Python API in the user's running Blender, so names match their version. Covers types and members (including add-on property groups such as `CyclesRenderSettings`), enum values filled in at runtime (render engines, view transforms), operator arguments, node input/output sockets, Python modules and functions, and word search.
- Manual-edit reporting: changes made in Blender outside the AI's commands (objects added, removed, moved or edited; materials, modifiers, mesh counts; selection, active object, mode, frame) are returned once as `user_edits` on the next reply. New addon preference **Report manual edits** (on by default).
- Per-command timeouts: `execute_blender_code` honours its `timeout` argument, `[bridge.command_timeouts]` in `config.toml` overrides individual commands, and renders, imports, exports and file operations get longer defaults (120–1800s, max 3600s).
- Bridge integration tests over real TCP sockets: large payloads, split multi-byte UTF-8, concurrent and out-of-order replies, bad input and dropped connections.

### Changed

- **Safe execution mode** (on by default) now checks scripts before they run and refuses ones that start programs, delete files, use the network, register classes/handlers/timers, change add-ons or preferences, quit or reset Blender, or use `eval`/`exec`/`__import__`/`importlib`. Each refusal names its line. Turn the mode off in the addon preferences if a script really needs one of these. It is a safety net, not a sandbox.
- Timeout errors say whether the command was cancelled before it started (nothing changed) or is still running in Blender (check the scene before retrying).
- `get_addon_status` warns when the installed addon lacks `lookup_api`. Reinstall it with `blender-mcp install-addon`.

### Fixed

- A command that timed out while queued no longer runs later in Blender, after nobody was waiting for it, which could make a retry do the work twice.
- Commands from a client that disconnected before they started are skipped.

## [1.3.0] - 2026-11-20

### Added

- Tool profiles. The default `core` profile exposes 12 tools centred on `execute_blender_code` and `look`; set `BLENDER_MCP_TOOL_PROFILE=full` (or `[tools] profile = "full"`) for all ~170 specialised tools.
- `look`: one screenshot tool with `mode` (viewport, material, rendered, wireframe, camera, angles), `view` and `max_size`, replacing the seven capture tools in the core profile.
- `execute_blender_code` preloads `bpy`, `mathutils`, `C` and `D`, and returns the value of a trailing expression when no `result` is set.

### Changed

- Server instructions now lead with `execute_blender_code` and cover common `bpy` pitfalls (localized node names, Blender 4.x Principled BSDF inputs, enum lookups, imported model scale).
- Screenshots use an off-screen viewport render, so popups, the splash screen and UI no longer appear in images; axis views are framed and the user's viewport is restored afterwards.
- `search_assets` defaults `source` to `polyhaven`.
- Script errors show only the frames from the submitted script.

### Fixed

- Functions, lambdas and comprehensions in `execute_blender_code` scripts can see the script's own imports and variables (previously `NameError`).

## [1.2.3] - 2026-11-20

### Changed

- The one-line installers (`install.ps1`, `install.sh`) now install from `main` instead of `develop`. Set `BLENDER_MCP_BRANCH` to use another branch.
- The scripts in `installers/` check out and fast-forward `main` (or `BLENDER_MCP_BRANCH`) before installing, and stop if the checkout is blocked by local changes.

## [1.2.2] - 2026-11-20

### Fixed

- Re-running the installer no longer fails when local changes block `git pull`: they are stashed (with restore instructions) before updating.
- The Windows installer stops running `blender-mcp` processes that lock `.venv\Scripts\blender-mcp.exe` before `uv sync` (previously "os error 32"), and ignores an unrelated activated `VIRTUAL_ENV`.
- The site's copy-command button works on insecure (non-HTTPS) origins.

## [1.2.1] - 2026-11-20

### Fixed

- `curl ... | sh` now works on Ubuntu and Debian, where `sh` is dash and rejected `set -o pipefail`.
- The Windows installer configures Claude Desktop from the Microsoft Store (its config lives under `%LOCALAPPDATA%\Packages\Claude_*`).
- The Windows installer stops with a clear message when `git`, `uv sync` or the addon install fails, instead of carrying on and installing a stale addon (for example when local changes block `git pull`).
- Reinstalling to another folder now updates an existing Codex `config.toml` entry instead of keeping the old path.

### Added

- End-to-end installer test in Docker (Ubuntu 22.04/24.04, Debian 12, Fedora 41): the `Installer (Docker)` workflow and `tests/installer/docker-test.sh`.

## [1.2.0] - 2026-11-20

### Added

- The Windows, macOS and Linux installers now register `blender-mcp` automatically in every AI client they find: Claude Desktop, Claude Code, Cursor, Windsurf, VS Code / VS Code Insiders, Cline, Roo Code, Gemini CLI and Codex. Missing configs are created, existing ones backed up to `*.blender-mcp.bak`, and other servers kept.

### Changed

- The Blender sidebar tab and panel are renamed from "AI / MCP" to "Blender MCP".

## [1.1.0] - 2026-11-20

### Added

- Screenshot and render tools return real MCP images, so the AI can see the viewport.
- `import_external_asset` downloads and imports assets end to end: Poly Haven models, HDRIs (world lighting) and PBR textures; Sketchfab and Poly Pizza models. `target_size` scales models, which are placed on the ground; replies include `world_bounding_box`.
- AI 3D generation with Meshy and Tripo: `generate_3d`, `get_generation_status`, `list_generation_jobs`.
- `get_addon_status` (versions, enabled libraries/generators, outdated-addon warnings), `get_guide` with bpy/materials/scene guides (also `blender://guides/*` resources), and `search_scene`.
- Downloads are HTTPS-only, size-limited and protected against path traversal / zip-slip.

### Fixed

- Blender MCP no longer collides with the third-party "MCP for Blender" addon: the default bridge port is now `9877` (was `9876`).
- On Windows the addon binds with `SO_EXCLUSIVEADDRUSE`, so a second addon on the same port fails loudly instead of silently stealing connections.
- The MCP server reports a clear "not the Blender MCP addon" error when a different service owns the port, instead of hanging until the auth timeout.

### Changed

- `execute_blender_code` is enabled by default (`script_permission=trusted`), matching "MCP for Blender". Set `restricted`/`confirmation` to lock it down.

## [1.0.2] - 2026-11-20

### Fixed

- Raise the MCP bridge TCP reader limit so viewport/render screenshot base64 payloads are not truncated (fixes `Connection lost` / WinError 10054 during capture)
- Actually downscale viewport screenshots to `max_size` instead of only returning the hint
- Reload shared addon helpers (e.g. `screenshots`) on handler register so disable/enable picks up helper fixes

## [1.0.1] - 2026-11-19

### Fixed

- Reload handler modules on addon register so commands work after disable/enable without restarting Blender
- Clear stale bridge RUNNING state when the accept loop exits; Start recovers automatically
- Authenticate the TCP client before starting the shared reader (avoids auth/read race)
- Handle `ErrorCode` membership correctly on Python 3.11+ (`StrEnum`)
- Connection Test now probes TCP instead of only reading in-memory state

## [1.0.0] - 2026-11-19

### Added

- Initial Blender MCP server and Blender addon bridge
- MCP tools for scene, objects, meshes, materials, modifiers, cameras, lights, rendering, screenshots, animation, collections, import/export, assets, and scripting
- MCP resources and workflow prompts
- Localhost TCP NDJSON bridge with auth token, heartbeats, and request IDs
- Security controls: script permission modes, path validation, destructive confirmation
- Poly Haven / Sketchfab / Poly Pizza provider integrations (optional credentials)
- Windows, Linux, and macOS installers driven by **uv**
- Documentation and GitHub community templates
- Branch protection and Git Flow conventions (`main`, `develop`, `feature/*`, `release/*`, `hotfix/*`)

## [0.1.0] - 2026-11-19

### Added

- First public project skeleton and Phase 1–8 foundation on branch `feature/blender-mcp-foundation`
