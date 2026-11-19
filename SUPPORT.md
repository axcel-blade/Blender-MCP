# Support

## Getting help

1. Read the docs:
   - [README.md](README.md)
   - [docs/INSTALLATION.md](docs/INSTALLATION.md)
   - [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
   - [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Search [existing issues](https://github.com/axcel-blade/Blender-MCP/issues)
3. Open a new issue with the appropriate template
4. For design or Q&A, start a [Discussion](https://github.com/axcel-blade/Blender-MCP/discussions) if enabled

## Diagnostics

Before asking for help, run:

```bash
uv sync
uv run blender-mcp diagnose
```

Include:

- OS and Blender version
- `blender-mcp` version (`uv run blender-mcp version`)
- MCP client (Cursor, Claude Desktop, etc.)
- Relevant logs from the Blender **AI / MCP** panel
- Redacted config (no secrets)

## What we can help with

- Installation and MCP client setup
- Addon/bridge connection problems
- Tool behavior and expected results
- Security configuration questions

## What we cannot help with here

- General Blender modeling tutorials unrelated to this project
- Third-party API billing for Sketchfab / Meshy / etc.
- Compromised machines or malware cleanup

## Security issues

See [SECURITY.md](SECURITY.md).
