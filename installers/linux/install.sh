#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Blender MCP installer (Linux)"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
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
ext = os.path.join("User", "globalStorage")
targets = [
    (os.path.join(home, ".cursor", "mcp.json"), "mcpServers", std),
    (os.path.join(appdata, "Claude", "claude_desktop_config.json"), "mcpServers", std),
    (os.path.join(home, ".codeium", "windsurf", "mcp_config.json"), "mcpServers", std),
    (os.path.join(home, ".gemini", "settings.json"), "mcpServers", std),
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
    text = open(toml, encoding="utf-8").read() if os.path.isfile(toml) else ""
    if "[mcp_servers.blender-mcp]" not in text:
        with open(toml, "a", encoding="utf-8") as f:
            f.write("\n[mcp_servers.blender-mcp]\ncommand = \"uv\"\nargs = " + json.dumps(args) + "\n")
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
