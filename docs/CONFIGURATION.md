# Configuration

Copy `config.example.toml` to `config.toml` or set environment variables with the `BLENDER_MCP_` prefix (see `.env.example`).

When a setting is given in more than one place, the first of these wins:

1. `BLENDER_MCP_*` environment variables, including ones in a `.env` file
2. `config.toml`
3. Built-in defaults

Only names with the `BLENDER_MCP_` prefix are read from the environment. Generic variables such as `PORT` or `HOST`, which other tools often set, are ignored.

Important keys:

| Setting | Default | Notes |
|---------|---------|-------|
| `bridge.host` | `127.0.0.1` | Blender bridge host |
| `bridge.port` | `9877` | Must match addon (9876 is used by the third-party "MCP for Blender") |
| `bridge.auth_token` | empty | Shared secret if set in addon prefs |
| `security.script_permission` | `trusted` | `restricted` / `confirmation` / `trusted` |
| `security.allowed_directories` | `[]` | Path allow-list |
| `blender.path` | empty (auto-detect) | Blender executable used by `open_blender`. Env: `BLENDER_MCP_BLENDER_PATH` |
| `blender.launch_timeout` | `60` | Seconds `open_blender` waits for the addon bridge. Env: `BLENDER_MCP_BLENDER_LAUNCH_TIMEOUT` |
| `tool_groups.*` | enabled | Disable capability groups |
| `providers.*` | mixed | External asset providers |

API keys must come from environment variables or addon preferences — never commit them.
