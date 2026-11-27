#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Blender MCP installer (macOS)"

BRANCH="${BLENDER_MCP_BRANCH:-main}"
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  echo "Checking out $BRANCH..."
  git -C "$ROOT" fetch origin "$BRANCH" || echo "warning: could not fetch $BRANCH" >&2
  git -C "$ROOT" checkout "$BRANCH"
  git -C "$ROOT" pull --ff-only origin "$BRANCH" || echo "warning: could not fast-forward $BRANCH" >&2
fi

if ! command -v uv >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install uv
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
fi

# Registers blender-mcp (pointing at $1) in every AI client found on this machine.
# A client counts as installed if its config folder or CLI exists. Existing
# configs are backed up to *.blender-mcp.bak; other servers are kept.
register_mcp_clients() {
  root="$1"
  echo "Configuring AI clients..."
  uv run --directory "$root" python - "$root" <<'PY' || echo "warning: could not update some AI client configs" >&2
import json, os, shutil, sys
root = sys.argv[1]
home = os.path.expanduser("~")
if sys.platform == "darwin":
    appdata = os.path.join(home, "Library", "Application Support")
else:
    appdata = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
args = ["run", "--directory", root, "blender-mcp"]
std = {"command": "uv", "args": args}
vsc = {"type": "stdio", "command": "uv", "args": args}
# Google Antigravity (app, IDE, CLI): ~/.gemini/config/mcp_config.json. Its default 180 s
# per tool call is shorter than long renders and bakes, so allow up to an hour.
ag = {"command": "uv", "args": args, "timeoutSeconds": 3600}
ag_home = os.path.join(home, ".gemini")
if os.path.isdir(os.path.join(ag_home, "antigravity")) or os.path.isdir(os.path.join(ag_home, "config")):
    os.makedirs(os.path.join(ag_home, "config"), exist_ok=True)
ext = os.path.join("User", "globalStorage")
targets = [
    (os.path.join(home, ".cursor", "mcp.json"), "mcpServers", std),
    (os.path.join(appdata, "Claude", "claude_desktop_config.json"), "mcpServers", std),
    (os.path.join(home, ".codeium", "windsurf", "mcp_config.json"), "mcpServers", std),
    (os.path.join(home, ".gemini", "settings.json"), "mcpServers", std),
    (os.path.join(home, ".gemini", "config", "mcp_config.json"), "mcpServers", ag),
    (os.path.join(appdata, "Code", ext, "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json"), "mcpServers", std),
    (os.path.join(appdata, "Code", ext, "rooveterinaryinc.roo-cline", "settings", "mcp_settings.json"), "mcpServers", std),
    (os.path.join(appdata, "Code", "User", "mcp.json"), "servers", vsc),
    (os.path.join(appdata, "Code - Insiders", "User", "mcp.json"), "servers", vsc),
]
for path, key, entry in targets:
    if not os.path.isdir(os.path.dirname(path)):
        continue
    data = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        if raw.strip():
            try:
                data = json.loads(raw)
            except ValueError:
                print(f"warning: skipped {path} (not plain JSON; comments?). Add blender-mcp manually.", file=sys.stderr)
                continue
        shutil.copyfile(path, path + ".blender-mcp.bak")
    if not isinstance(data.get(key), dict):
        data[key] = {}
    data[key]["blender-mcp"] = entry
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"Configured {path}")
toml = os.path.join(home, ".codex", "config.toml")
if not shutil.which("codex") and os.path.isdir(os.path.dirname(toml)):
    import re
    text = open(toml, encoding="utf-8").read() if os.path.isfile(toml) else ""
    if text:
        shutil.copyfile(toml, toml + ".blender-mcp.bak")
    # Drop any existing blender-mcp table (and its sub-tables), then append a fresh one,
    # so a reinstall to another folder updates the path instead of keeping the old one.
    text = re.sub(r"(?ms)^\[mcp_servers\.blender-mcp(?:\.[^\]]*)?\][^\n]*\n.*?(?=^\[(?!mcp_servers\.blender-mcp[\].])|\Z)", "", text)
    text = text.rstrip() + ("\n\n" if text.strip() else "")
    text += "[mcp_servers.blender-mcp]\ncommand = \"uv\"\nargs = " + json.dumps(args) + "\n"
    with open(toml, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Configured {toml}")
PY
  if command -v claude >/dev/null 2>&1; then
    claude mcp remove --scope user blender-mcp >/dev/null 2>&1 || true
    if claude mcp add --scope user blender-mcp -- uv run --directory "$root" blender-mcp >/dev/null 2>&1; then
      echo "Configured Claude Code (user scope)"
    else
      echo "warning: 'claude mcp add' failed. Add blender-mcp manually." >&2
    fi
  fi
  if command -v codex >/dev/null 2>&1; then
    codex mcp remove blender-mcp >/dev/null 2>&1 || true
    if codex mcp add blender-mcp -- uv run --directory "$root" blender-mcp >/dev/null 2>&1; then
      echo "Configured Codex"
    else
      echo "warning: 'codex mcp add' failed. Add blender-mcp manually." >&2
    fi
  fi
}

cd "$ROOT"
uv sync
uv run blender-mcp install-addon
register_mcp_clients "$ROOT"

echo "Enable the addon in Blender: Edit → Preferences → Add-ons → Blender MCP"
echo "Restart your AI client(s). Others: uv run --directory \"$ROOT\" blender-mcp"
