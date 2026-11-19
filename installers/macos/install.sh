#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Blender MCP installer (macOS)"

if ! command -v uv >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install uv
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
fi

cd "$ROOT"
uv sync
uv run blender-mcp install-addon

echo "Enable the addon in Blender: Edit → Preferences → Add-ons → Blender MCP"
echo "Configure your MCP client to run: uv run --directory \"$ROOT\" blender-mcp"
