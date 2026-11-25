# Blender MCP

[![CI](https://github.com/axcel-blade/Blender-MCP/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/axcel-blade/Blender-MCP/actions/workflows/ci.yml)
[![CD](https://github.com/axcel-blade/Blender-MCP/actions/workflows/cd.yml/badge.svg)](https://github.com/axcel-blade/Blender-MCP/actions/workflows/cd.yml)
[![Latest release](https://img.shields.io/github/v/release/axcel-blade/Blender-MCP?display_name=tag&logo=github)](https://github.com/axcel-blade/Blender-MCP/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-c4f82a)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/packaging-uv-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Blender](https://img.shields.io/badge/Blender-3.6%2B%20%7C%204.x-E87D0D?logo=blender&logoColor=white)](https://www.blender.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-555)](docs/ARCHITECTURE.md)
[![Local only](https://img.shields.io/badge/bridge-localhost%20default-555)](SECURITY.md)

Production-oriented **Model Context Protocol (MCP)** integration for Blender. AI clients (Claude Desktop, Cursor, VS Code, Codex, Windsurf, and others) can inspect scenes, model, shade, light, render, and visually verify work through a local bridge.

This project is **not** affiliated with the Blender Foundation.

## Features

- MCP stdio server + Blender addon TCP bridge (localhost by default)
- Scene inspection, object/mesh modeling, materials, modifiers, cameras, lights
- Geometry Nodes helpers with socket inspection
- Viewport screenshots and render previews for visual verification
- Animation keyframes, import/export, project save/load
- Optional asset providers (Poly Haven, Sketchfab, Poly Pizza, AI 3D stubs)
- Script execution with explicit permission modes (restricted / confirmation / trusted)
- Auth token, path allow-lists, render limits, tool-group toggles

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (required)
- Blender 3.6+ (4.x recommended)

## Quick start

Install site (Astro / GitHub Pages): [axcel-blade.github.io/Blender-MCP](https://axcel-blade.github.io/Blender-MCP/)

**Windows (PowerShell):** press **Win+R**, type `powershell` and press **Enter** (no admin needed). Paste the command below with a right-click or **Ctrl+V**, then press **Enter**:

```powershell
irm https://axcel-blade.github.io/Blender-MCP/install.ps1 | iex
```

**macOS / Linux:** open **Terminal** (macOS: **Cmd+Space**, type Terminal; Linux: **Ctrl+Alt+T**). Paste the command below (**Cmd+V** on macOS, **Ctrl+Shift+V** on Linux), then press **Enter**:

```bash
curl -LsSf https://axcel-blade.github.io/Blender-MCP/install.sh | sh
```

Or install manually from a clone with uv (needs uv, Git and Blender 3.6+; use uv, not pip):

```powershell
git clone https://github.com/axcel-blade/Blender-MCP.git
cd Blender-MCP
uv sync
uv run blender-mcp install-addon
```

Manual installs don't configure your AI client; see [Manual client config](#manual-client-config) below. Full steps, including installing the add-on from a release zip, are in [docs/INSTALLATION.md](docs/INSTALLATION.md#manual-install).

1. Blender → **Edit → Preferences → Add-ons** → enable **Blender MCP**
2. 3D Viewport → press **N** → **Blender MCP** → **Start**
3. Fully quit and reopen your AI client.

### Automatic client config

The one-line and local-clone installers register `blender-mcp`, with the real install path, in every AI client they find. You don't need to edit any config by hand:

- Claude Desktop, Claude Code
- Cursor, Windsurf
- VS Code / VS Code Insiders (Copilot), Cline, Roo Code
- Gemini CLI, Codex

A client is set up only if it's installed. Existing configs are backed up to `*.blender-mcp.bak` and your other servers are kept. Re-running the installer is safe. Paths per OS are in [docs/INSTALLATION.md](docs/INSTALLATION.md).

### Manual client config

For any other client, or if you ran only `uv sync` + `install-addon`, point it at your clone:

```json
{
  "mcpServers": {
    "blender-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "C:/path/to/Blender-MCP", "blender-mcp"]
    }
  }
}
```

## Tool profiles

By default the server exposes a **core** profile of 16 tools: `get_addon_status`,
`get_scene_info`, `get_object_info`, `search_scene`, `execute_blender_code`, `lookup_api`,
`look`, `search_assets`, `import_external_asset`, `generate_3d`, `get_generation_status`,
`get_guide`, `blender_mcp_version`, `open_blender`, `close_blender`, and `blend_file`
(open, save, rename and manage `.blend` files). Models choose tools more reliably from a short
list, and `execute_blender_code` already covers the whole `bpy` API.

To expose all ~340 specialised wrapper tools (sculpting, rigging, physics, compositing, VSE, Grease Pencil, environments, QC, batch automation, ...) instead, set `BLENDER_MCP_TOOL_PROFILE=full`
or put `profile = "full"` under `[tools]` in `config.toml`.

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Install & MCP client setup |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Config & environment |
| [docs/TOOLS.md](docs/TOOLS.md) | MCP tools overview |
| [docs/SECURITY.md](docs/SECURITY.md) | Technical security controls |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common failures |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Git Flow & contribution guide |
| [SUPPORT.md](SUPPORT.md) | How to get help |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards |
| [LICENSE](LICENSE) | MIT license |

## Architecture

```
AI Client --stdio MCP--> blender-mcp server --TCP NDJSON--> Blender addon --bpy--> Blender
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Git Flow

| Branch | Purpose |
|--------|---------|
| `main` | Production releases |
| `develop` | Integration |
| `feature/*` | Features → `develop` |
| `release/*` | Release prep → `main` + `develop` |
| `hotfix/*` | Urgent fixes from `main` |

Details: [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

- Bridge binds to `127.0.0.1` unless remote mode is explicitly enabled
- Optional shared auth token
- `execute_blender_code` is **not a sandbox** — the default is `script_permission=trusted` (same as "MCP for Blender"); set it to `restricted` or `confirmation` if you do not trust the client
- Path allow-lists for file operations when configured

Report vulnerabilities privately via [SECURITY.md](SECURITY.md).

## Development

This project is managed exclusively with **uv** (lockfile + virtualenv).

```powershell
uv sync
uv run pytest
uv run ruff check src tests
uv run pyright
```

Diagnose a live Blender connection:

```powershell
uv run blender-mcp diagnose
```

## License

MIT © AXCEL BLADE — see [LICENSE](LICENSE).

External asset providers retain their own licenses and attribution requirements.
