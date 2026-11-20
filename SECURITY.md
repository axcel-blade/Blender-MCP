# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes |
| 0.1.x   | No |
| < 0.1   | No |

## Reporting a vulnerability

Do **not** open a public issue for security vulnerabilities.

Please report privately using one of these options:

1. GitHub **Security Advisories** for this repository (preferred)
2. Contact maintainers via the channels listed in [SUPPORT.md](SUPPORT.md)

Include:

- Description of the issue
- Steps to reproduce
- Affected version / commit
- Potential impact
- Any suggested fix (optional)

We aim to acknowledge reports within **7 days** and provide a status update within **14 days**.

## Security notes for users

- The Blender bridge defaults to **localhost only**
- Keep `script_permission=restricted` unless you fully trust the MCP client
- `execute_blender_code` is powerful and is **not a secure sandbox**
- With **Safe execution mode** on (the addon default), scripts are checked before they
  run and refused if they start programs, delete files, use the network, register
  classes/handlers/timers, enable add-ons, change or save preferences, quit or reset
  Blender, or use `eval`/`exec`/`__import__`/`importlib`/escape-hatch dunders. This
  stops accidents and obvious misuse; Python is too dynamic for inspection to be
  airtight, so don't treat it as isolation.
- Never commit API keys or auth tokens
- Do not expose the bridge to the public internet

Technical hardening details: [docs/SECURITY.md](docs/SECURITY.md)
