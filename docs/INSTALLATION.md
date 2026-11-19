# Installation

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (installs and pins Python 3.11 via `.python-version`)
- Blender 3.6+ (4.x recommended)

Do **not** use `pip install` for this project. Use `uv sync` / `uv run`.

## Windows

```powershell
.\installers\windows\install.ps1
```

Manual:

```powershell
uv sync
uv run blender-mcp install-addon
```

## Linux / macOS

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
