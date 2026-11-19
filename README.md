# Blender MCP

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

## Quick start (Windows)

```powershell
.\installers\windows\install.ps1
```

Or manually with uv:

```powershell
uv sync
uv run blender-mcp install-addon
```

1. Blender → **Edit → Preferences → Add-ons** → enable **Blender MCP**
2. 3D Viewport → press **N** → **AI / MCP** → **Start**
3. Point your MCP client at:

```json
{
  "mcpServers": {
    "blender": {
      "command": "uv",
      "args": ["run", "--directory", "C:/path/to/Blender-MCP", "blender-mcp"]
    }
  }
}
```

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
- `execute_blender_code` is **not a sandbox** — keep `script_permission=restricted` unless you trust the client
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
