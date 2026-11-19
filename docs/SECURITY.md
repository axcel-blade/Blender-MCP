# Security

## Defaults

- Localhost-only bridge
- Restricted script execution
- Destructive deletes require `confirmed=true`
- File overwrite protection unless authorized

## Script execution

`execute_blender_code` runs inside the Blender process. Keyword filters are **not** a sandbox. Only enable confirmation/trusted modes when you accept that risk.

## Remote exposure

Do not bind the bridge to public interfaces. If you must use LAN access, prefer an SSH tunnel to localhost and keep an auth token set.
