"""How long each bridge command may take, and what to say when it takes longer."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

# The server only rejects nonsense; the addon additionally enforces a 1s floor.
MIN_TIMEOUT = 0.01
MAX_TIMEOUT = 3600.0

# Extra seconds the server waits beyond the timeout it sends to the addon, so the
# addon's own (more specific) timeout reply arrives before the server gives up.
RESPONSE_GRACE = 10.0

# Commands that routinely outlast the default. Config `command_timeouts` overrides these.
SLOW_COMMAND_TIMEOUTS: dict[str, float] = {
    "render_scene": 600.0,
    "render_final": 600.0,
    "render_animation": 1800.0,
    "render_preview": 300.0,
    "capture_render": 300.0,
    "inspect_render": 300.0,
    "create_animation_preview": 300.0,
    "import_polyhaven_asset": 300.0,
    "import_local_asset": 300.0,
    "import_asset": 300.0,
    "export_asset": 300.0,
    "export_selected_objects": 300.0,
    "export_scene": 300.0,
    "open_blend_file": 300.0,
    "save_blend_file": 120.0,
    "save_as": 120.0,
    "remesh_mesh": 300.0,
    "apply_modifier": 300.0,
}


def _valid(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(seconds) or seconds <= 0:
        return None
    return seconds


def resolve_timeout(
    command: str,
    params: Mapping[str, Any] | None,
    default: float,
    overrides: Mapping[str, float] | None = None,
    explicit: float | None = None,
) -> float:
    """Pick the timeout for ``command``, clamped to [MIN_TIMEOUT, MAX_TIMEOUT].

    Precedence: ``explicit`` argument, then a ``timeout`` in the command's params
    (e.g. execute_blender_code), then config ``command_timeouts``, then the built-in
    slow-command table, then ``default``.
    """
    candidates = (
        explicit,
        (params or {}).get("timeout"),
        (overrides or {}).get(command),
        SLOW_COMMAND_TIMEOUTS.get(command),
        default,
    )
    for candidate in candidates:
        seconds = _valid(candidate)
        if seconds is not None:
            return max(MIN_TIMEOUT, min(seconds, MAX_TIMEOUT))
    return max(MIN_TIMEOUT, min(60.0, MAX_TIMEOUT))


def no_reply_message(command: str, seconds: float) -> str:
    """Message for when Blender sent nothing back at all (not even its own timeout)."""
    return (
        f"No reply from Blender for '{command}' after {seconds:g}s. Blender is probably "
        "frozen or stuck in a long operation (a render, a large import, exact booleans) "
        "that can't be interrupted from here, and the command may still complete. Check "
        "that Blender responds, then inspect the scene (get_scene_info or look) before "
        "retrying so the work doesn't happen twice. For long jobs pass a larger timeout "
        "or split the work into smaller steps."
    )
