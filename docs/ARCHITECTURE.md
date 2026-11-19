# Architecture

## Overview

Blender MCP connects AI clients to a running Blender instance through the Model Context Protocol.

```
AI Client (Claude / Cursor / VS Code / …)
        │  MCP stdio
        ▼
┌───────────────────────────┐
│  blender-mcp (Python)     │
│  FastMCP tools/resources  │
│  Bridge client + security │
└─────────────┬─────────────┘
              │  TCP localhost, NDJSON, auth token
              ▼
┌───────────────────────────┐
│  Blender Addon            │
│  Bridge server + N-panel  │
│  Main-thread exec queue   │
│  Command handlers (bpy)   │
└───────────────────────────┘
```

## Design principles

1. **Modular packages** — MCP tools, resources, prompts, providers, and addon handlers are separate modules.
2. **Request IDs + heartbeats** — correlate responses, detect dead connections, support timeouts cleanly.
3. **Auth token** — optional shared secret on the bridge.
4. **Script permission modes** — restricted / confirmation / trusted with explicit policy.
5. **Path validation** — allowed directories for import/export/script file access.
6. **Tool groups** — enable/disable capability sets from config and addon UI.
7. **Pydantic settings** — typed config from TOML + environment overrides for secrets.
8. **No bpy in MCP process** — server never imports Blender; all bpy work stays in the addon.

## Implementation phases

1. Foundation: bridge, server, addon UI, scene inspection, diagnostics
2. Core modeling: create/modify/delete objects, transforms, collections
3. Materials & modifiers (+ geometry nodes foundation)
4. Cameras & lighting
5. Visual feedback (screenshots / previews)
6. Rendering & project I/O
7. Animation, assets, scripting
8. Installers & documentation

## Attribution

- Blender is © Blender Foundation; this project is not affiliated with the Blender Foundation.
- External asset providers retain their own licenses and attribution requirements.
