"""Enable Blender MCP and ensure the TCP bridge is listening (for local smoke tests)."""

from __future__ import annotations

import addon_utils
import bpy


MODULE = "blender_mcp_addon"


def _enable_addon() -> None:
    # Disable first so register() always runs cleanly (handlers + auto-start).
    try:
        addon_utils.disable(MODULE, default_set=True)
    except Exception as exc:  # noqa: BLE001
        print(f"Disable note: {exc}")

    try:
        addon_utils.enable(MODULE, default_set=True, persistent=True)
        print(f"Enabled addon: {MODULE}")
    except Exception as exc:  # noqa: BLE001
        print(f"Could not enable {MODULE}: {exc}")
        raise RuntimeError("Blender MCP addon is not installed") from exc


def _ensure_bridge() -> None:
    import importlib

    pkg = importlib.import_module(MODULE)
    bridge_server = importlib.import_module(f"{MODULE}.bridge_server")
    handlers = importlib.import_module(f"{MODULE}.handlers")

    # Guarantee command handlers are registered even if enable() was a no-op.
    handlers.register()
    registered = sorted(handlers._REGISTRY.keys())
    print(f"Registered commands ({len(registered)}): {registered[:8]}...")

    if not bridge_server.is_server_alive():
        bridge_server.start_server()

    state = bridge_server.get_state()
    probe = bridge_server.probe_listen()
    print(f"Addon version: {getattr(pkg, 'ADDON_VERSION', '?')}")
    print(f"Bridge state: {state}")
    print(f"Bridge probe: {probe}")
    if not probe.get("ok"):
        raise RuntimeError(f"Bridge not accepting connections: {probe}")
    if "get_scene_info" not in handlers._REGISTRY:
        raise RuntimeError("Handlers failed to register get_scene_info")


_enable_addon()
_ensure_bridge()
print("Blender MCP bridge is ready")
