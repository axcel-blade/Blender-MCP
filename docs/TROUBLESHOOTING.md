# Troubleshooting

| Problem | Fix |
|---------|-----|
| `BLENDER_NOT_CONNECTED` | Start the addon bridge (N-panel → AI / MCP → Start). Confirm port matches config. |
| Auth failed | Match `auth_token` in addon preferences and `BLENDER_MCP_AUTH_TOKEN` / config. |
| Script permission denied | Set addon script permission to confirmation/trusted intentionally. |
| Timeout | Break work into smaller steps; raise request timeout. |
| No screenshot | Ensure a 3D Viewport is visible in Blender. |
| MCP client doesn't see tools | Restart the client after config changes; run only one Blender MCP server instance. |

Run diagnostics:

```bash
uv run blender-mcp diagnose
```
