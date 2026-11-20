# Troubleshooting

| Problem | Fix |
|---------|-----|
| `BLENDER_NOT_CONNECTED` / connection refused | **Blender must be open** with the Blender MCP addon enabled and the bridge **RUNNING** (N-panel → Blender MCP → Start). A running `blender-mcp` MCP process alone does **not** open port 9876 — that listener lives inside Blender. Confirm port matches config (`127.0.0.1:9876` by default). |
| `Connection lost` / WinError 10054 during viewport/render capture | Fixed by raising the MCP client's NDJSON reader limit (screenshots embed large base64 in one line). Update the MCP server package and restart the Cursor Blender MCP entry; disable/enable the Blender addon (or restart Blender) so screenshot downscaling helpers reload. |
| Auth failed | Match `auth_token` in addon preferences and `BLENDER_MCP_AUTH_TOKEN` / config. |
| Script permission denied | Set addon script permission to confirmation/trusted intentionally. |
| Timeout | Break work into smaller steps; raise request timeout. |
| No screenshot | Ensure a 3D Viewport is visible in Blender. |
| MCP client doesn't see tools | Restart the client after config changes; run only one Blender MCP server instance. |
| Panel says RUNNING but clients still fail | Press **Stop**, then **Start**, or restart Blender. Use **Connection Test** (probes TCP). Stale state after an accept-loop crash is recovered automatically on Start in current builds. |
| `Unknown command` after disable/enable | Fixed in current builds by reloading handler modules on register. Update/reinstall the addon, or restart Blender once. |
| Port busy / wrong addon | Disable other MCP addons (e.g. third-party “MCP for Blender”) that use the same port (Blender MCP now defaults to `9877`; "MCP for Blender" uses `9876`). |

## Connection checklist

1. Launch Blender.
2. Preferences → Add-ons → enable **Blender MCP** (auto-start is on by default).
3. Confirm View3D sidebar **Blender MCP** shows **RUNNING**.
4. Run `uv run blender-mcp diagnose` or your MCP client's diagnose tool.
5. Port/token must match between addon prefs and MCP config / env.

Run diagnostics:

```bash
uv run blender-mcp diagnose
```
