#!/bin/sh
# End-to-end test of the macOS/Linux installers inside a throwaway Linux container.
# Runs as root in a fresh image (Ubuntu, Debian, Fedora, ...). Never run it on your own machine:
# it writes to $HOME. Use tests/installer/docker-test.sh or the "Installer (Docker)" workflow.
#
# Usage: run-in-container.sh <path to repo checkout>
#
# 1. Installs git + curl.
# 2. Snapshots the checkout (including uncommitted changes) into a temp git repo.
# 3. Fakes a Blender install and AI client folders under $HOME.
# 4. Runs site/public/install.sh through `sh` (exactly like `curl ... | sh`), twice.
# 5. Runs installers/linux/install.sh through bash.
# 6. Checks every client config points at the right install dir, with no duplicates.

set -eu

SRC="${1:?usage: run-in-container.sh <repo checkout>}"

log() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nFAIL: %s\n' "$*" >&2; exit 1; }

log "Installing git and curl"
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null
  apt-get install -y -qq git curl ca-certificates >/dev/null
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y -q git curl >/dev/null
elif command -v apk >/dev/null 2>&1; then
  apk add -q git curl bash
else
  fail "no supported package manager in this image"
fi
git config --global --add safe.directory '*'

log "Snapshotting $SRC"
REPO=/tmp/blender-mcp-src
rm -rf "$REPO"
mkdir -p "$REPO"
# Tracked + untracked-but-not-ignored files, so local uncommitted changes are tested too.
(cd "$SRC" && git ls-files -co --exclude-standard -z | xargs -0 tar -cf - --) | tar -xf - -C "$REPO"
git -C "$REPO" init -q -b ci-under-test
git -C "$REPO" add -A
git -C "$REPO" -c user.name=ci -c user.email=ci@localhost commit -qm "installer test snapshot"

log "Faking Blender and AI client folders"
mkdir -p \
  "$HOME/.config/blender/4.2/scripts/addons" \
  "$HOME/.cursor" \
  "$HOME/.codeium/windsurf" \
  "$HOME/.gemini/antigravity" \
  "$HOME/.codex" \
  "$HOME/.config/Claude" \
  "$HOME/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings"
# An existing config with another server: it must survive.
printf '{"mcpServers":{"other":{"command":"x"}},"theme":"dark"}\n' > "$HOME/.cursor/mcp.json"

INSTALL_DIR="$HOME/Blender-MCP"
export BLENDER_MCP_REPO="$REPO" BLENDER_MCP_BRANCH=ci-under-test BLENDER_MCP_HOME="$INSTALL_DIR"

log "One-line installer via sh (fresh clone)"
sh < "$REPO/site/public/install.sh"
export PATH="$HOME/.local/bin:$PATH"

log "One-line installer via sh again (update path, must be idempotent)"
sh < "$REPO/site/public/install.sh"

check() {
  root="$1"
  uv run --directory "$INSTALL_DIR" python - "$root" <<'PY'
import json, os, sys
root = sys.argv[1]
home = os.path.expanduser("~")
expected = ["run", "--directory", root, "blender-mcp"]
files = {
    ".cursor/mcp.json": "mcpServers",
    ".codeium/windsurf/mcp_config.json": "mcpServers",
    ".gemini/settings.json": "mcpServers",
    ".gemini/config/mcp_config.json": "mcpServers",
    ".config/Claude/claude_desktop_config.json": "mcpServers",
    ".config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json": "mcpServers",
}
bad = []
for rel, key in files.items():
    path = os.path.join(home, rel)
    try:
        entry = json.load(open(path))[key]["blender-mcp"]
    except Exception as e:
        bad.append(f"{rel}: no blender-mcp entry ({e})")
        continue
    if entry.get("command") != "uv" or entry.get("args") != expected:
        bad.append(f"{rel}: wrong entry {entry}")
ag = json.load(open(os.path.join(home, ".gemini/config/mcp_config.json")))["mcpServers"]["blender-mcp"]
if ag.get("timeoutSeconds") != 3600:
    bad.append(f".gemini/config/mcp_config.json: expected timeoutSeconds 3600, got {ag.get('timeoutSeconds')}")
if "other" not in json.load(open(os.path.join(home, ".cursor/mcp.json")))["mcpServers"]:
    bad.append(".cursor/mcp.json: existing 'other' server was lost")
toml = open(os.path.join(home, ".codex/config.toml")).read()
if toml.count("[mcp_servers.blender-mcp]") != 1:
    bad.append(f".codex/config.toml: expected 1 blender-mcp table, found {toml.count('[mcp_servers.blender-mcp]')}")
if root not in toml:
    bad.append(".codex/config.toml: wrong install path")
if not os.path.isdir(os.path.join(home, ".config/blender/4.2/scripts/addons/blender_mcp_addon")):
    bad.append("Blender addon was not installed")
if bad:
    print("\n".join("  - " + b for b in bad))
    sys.exit(1)
print(f"  all client configs point at {root}")
PY
}

log "Checking configs after one-line installer"
check "$INSTALL_DIR" || fail "one-line installer produced wrong configs"

log "Linux clone installer via bash"
bash "$REPO/installers/linux/install.sh"
check "$REPO" || fail "installers/linux/install.sh produced wrong configs"

log "PASS"
