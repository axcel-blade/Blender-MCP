# Installation

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (installed automatically by the remote installer)
- Git
- Blender 3.6+ (4.x recommended)

Do **not** use `pip install` for this project. Use `uv sync` / `uv run`.

## One-line install (GitHub Pages)

Site: [https://axcel-blade.github.io/Blender-MCP/](https://axcel-blade.github.io/Blender-MCP/)

**Windows (PowerShell):**

```powershell
irm https://axcel-blade.github.io/Blender-MCP/install.ps1 | iex
```

**macOS / Linux:**

```bash
curl -LsSf https://axcel-blade.github.io/Blender-MCP/install.sh | sh
```

This clones into `~/Blender-MCP` (override with `BLENDER_MCP_HOME`), checks out `develop` (override with `BLENDER_MCP_BRANCH`), runs `uv sync`, and installs the addon.

## Local clone install

### Windows

```powershell
.\installers\windows\install.ps1
```

Manual:

```powershell
uv sync
uv run blender-mcp install-addon
```

### Linux / macOS

```bash
chmod +x installers/linux/install.sh installers/macos/install.sh
./installers/linux/install.sh   # or macos
```

Manual:

```bash
uv sync
uv run blender-mcp install-addon
```

## Manual addon install

```bash
uv run blender-mcp pack-addon -o blender_mcp_addon.zip
```

In Blender: **Edit → Preferences → Add-ons → Install…** and select the zip, then enable **Blender MCP**.

## MCP clients

Configure a `blender` server entry that runs:

```bash
uv run --directory /path/to/Blender-MCP blender-mcp
```

Fully quit and reopen the client after editing MCP config.

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
