# Installation

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (installed automatically by the remote installer)
- Git
- Blender 3.6+ (4.x recommended)

Do **not** use `pip install` for this project. Use `uv sync` / `uv run`.

## One-line install (GitHub Pages)

Site: [https://axcel-blade.github.io/Blender-MCP/](https://axcel-blade.github.io/Blender-MCP/)

**Windows (PowerShell):** press **Win+R**, type `powershell` and press **Enter** (no admin needed). Paste the command below with a right-click or **Ctrl+V**, then press **Enter**:

```powershell
irm https://axcel-blade.github.io/Blender-MCP/install.ps1 | iex
```

**macOS / Linux:** open **Terminal** (macOS: **Cmd+Space**, type Terminal; Linux: **Ctrl+Alt+T**). Paste the command below (**Cmd+V** on macOS, **Ctrl+Shift+V** on Linux), then press **Enter**:

```bash
curl -LsSf https://axcel-blade.github.io/Blender-MCP/install.sh | sh
```

This clones into `~/Blender-MCP` (override with `BLENDER_MCP_HOME`), checks out `main` (override with `BLENDER_MCP_BRANCH`), runs `uv sync`, and installs the addon.

The installers (Windows, macOS and Linux, one-line or local clone) also register `blender-mcp` with the real install path in every AI client they find:

| Client | Windows | macOS / Linux |
| --- | --- | --- |
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` | `~/Library/Application Support/Claude/…` / `~/.config/Claude/…` |
| Claude Code | `claude mcp add --scope user` | same |
| Cursor | `%USERPROFILE%\.cursor\mcp.json` | `~/.cursor/mcp.json` |
| Windsurf | `%USERPROFILE%\.codeium\windsurf\mcp_config.json` | `~/.codeium/windsurf/mcp_config.json` |
| VS Code / Insiders (Copilot) | `%APPDATA%\Code\User\mcp.json` (`servers` key) | `Code/User/mcp.json` under Application Support / `~/.config` |
| Cline, Roo Code | their VS Code extension settings files | same |
| Gemini CLI | `%USERPROFILE%\.gemini\settings.json` | `~/.gemini/settings.json` |
| Codex | `codex mcp add`, else `%USERPROFILE%\.codex\config.toml` | `codex mcp add`, else `~/.codex/config.toml` |

A client is configured only if its folder or CLI exists; missing config files are created, and existing ones are backed up to `*.blender-mcp.bak` first. Files containing comments (JSONC) are skipped with a warning, so add the entry by hand there. Rerunning the installer is safe.

## Local clone install

Run the installer from a clone. Like the one-line install, it also configures your AI clients.

### Windows

```powershell
.\installers\windows\install.ps1
```

### Linux / macOS

```bash
chmod +x installers/linux/install.sh installers/macos/install.sh
./installers/linux/install.sh   # or macos
```

## Manual install

Use this if you'd rather not run an installer script. You need uv, Git and Blender 3.6+ (see [Prerequisites](#prerequisites)).

1. Clone the repository and install dependencies:

   ```bash
   git clone https://github.com/axcel-blade/Blender-MCP.git
   cd Blender-MCP
   uv sync
   ```

2. Install the Blender add-on:

   ```bash
   uv run blender-mcp install-addon
   ```

   Or install it from a zip: download `blender_mcp_addon-*.zip` from the [latest GitHub Release](https://github.com/axcel-blade/Blender-MCP/releases/latest), or pack one from your clone with `uv run blender-mcp pack-addon -o blender_mcp_addon.zip`. Then in Blender go to **Edit → Preferences → Add-ons → Install…** and select the zip.

3. Configure your MCP client (see [MCP clients](#mcp-clients)). A manual install doesn't do this for you.

4. In Blender, enable **Blender MCP** under **Edit → Preferences → Add-ons**, then in the 3D Viewport press **N** → **Blender MCP** → **Start**.

5. Fully quit and reopen your MCP client.

## MCP clients

Configure a `blender` server entry that runs:

```bash
uv run --directory /path/to/Blender-MCP blender-mcp
```

Replace `/path/to/Blender-MCP` with the full path to your clone. Fully quit and reopen the client after editing MCP config.

## Enabling GitHub Pages (maintainers)

1. Repo **Settings → Pages**
2. **Source**: GitHub Actions
3. Push to `develop` or `main` (or run the **Pages** workflow manually)

The site is an **Astro** app in `site/` managed with **pnpm**. CI runs `pnpm install --frozen-lockfile && pnpm build` and deploys `site/dist`.

Local preview:

```bash
cd site
pnpm install
pnpm dev
```

### Docker

Production-like static image (nginx on port 8080):

```bash
cd site
docker compose up --build
# http://localhost:8080/
# http://localhost:8080/install.ps1
```

Dev server with hot reload:

```bash
cd site
docker compose -f docker-compose.dev.yml up --build
# http://localhost:4321/
```

Build args (optional):

```bash
docker build \
  --build-arg ASTRO_SITE=https://axcel-blade.github.io \
  --build-arg ASTRO_BASE=/Blender-MCP \
  -t blender-mcp-site \
  .
```
