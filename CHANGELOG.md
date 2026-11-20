# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- Raise the MCP bridge TCP reader limit so viewport/render screenshot base64 payloads are not truncated (fixes `Connection lost` / WinError 10054 during capture)
- Actually downscale viewport screenshots to `max_size` instead of only returning the hint
- Reload shared addon helpers (e.g. `screenshots`) on handler register so disable/enable picks up helper fixes

### Added

- 

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
