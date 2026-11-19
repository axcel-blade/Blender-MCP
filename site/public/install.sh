#!/usr/bin/env bash
# Blender MCP remote installer (macOS / Linux)
# Usage:
#   curl -LsSf https://axcel-blade.github.io/Blender-MCP/install.sh | sh

set -euo pipefail

REPO_URL="https://github.com/axcel-blade/Blender-MCP.git"
BRANCH="${BLENDER_MCP_BRANCH:-develop}"
INSTALL_DIR="${BLENDER_MCP_HOME:-$HOME/Blender-MCP}"

echo "Blender MCP installer"
echo "Install dir: $INSTALL_DIR"
echo "Branch:      $BRANCH"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "Updating existing clone..."
  cd "$INSTALL_DIR"
  git fetch origin
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
else
  if [ -e "$INSTALL_DIR" ]; then
    echo "Directory exists but is not a git repo: $INSTALL_DIR" >&2
    echo "Set BLENDER_MCP_HOME or remove it." >&2
    exit 1
  fi
  echo "Cloning $REPO_URL ($BRANCH)..."
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

uv sync
uv run blender-mcp install-addon

echo ""
echo "Next steps:"
echo "1. Enable the addon in Blender: Edit → Preferences → Add-ons → Blender MCP"
echo "2. 3D Viewport → N → AI / MCP → Start"
echo "3. Configure your MCP client:"
echo "   uv run --directory \"$INSTALL_DIR\" blender-mcp"
echo "Done. Repo: $INSTALL_DIR"
