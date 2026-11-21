"""Track unsaved changes, including ones made by scripts.

``bpy.data.is_dirty`` only follows undo pushes, so edits made through the bridge
(from a timer, with no undo step) leave it False. A depsgraph handler catches them.
"""

from __future__ import annotations

_state = {"changed": False}


def _on_change(*_args) -> None:
    _state["changed"] = True


def _on_clean(*_args) -> None:
    _state["changed"] = False


def has_unsaved_changes() -> bool:
    import bpy

    return bool(bpy.data.is_dirty or _state["changed"])


def mark(changed: bool) -> None:
    _state["changed"] = changed


def _handlers():
    import bpy

    h = bpy.app.handlers
    return (
        (h.depsgraph_update_post, _on_change),
        (h.save_post, _on_clean),
        (h.load_post, _on_clean),
    )


def register() -> None:
    from bpy.app.handlers import persistent

    persistent(_on_change)
    persistent(_on_clean)
    for handler_list, fn in _handlers():
        # Drop copies left by a previous load of this module (addon reloads).
        for existing in [
            f
            for f in handler_list
            if getattr(f, "__name__", "") == fn.__name__
            and getattr(f, "__module__", "") == __name__
        ]:
            handler_list.remove(existing)
        handler_list.append(fn)


def unregister() -> None:
    for handler_list, fn in _handlers():
        if fn in handler_list:
            handler_list.remove(fn)
