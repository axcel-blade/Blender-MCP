# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- Re-running the installer on an install cloned before 1.2.3 no longer fails at `git checkout main`: those clones were `--single-branch` on `develop`, so the installer now adds the target branch to `origin` before fetching.

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
