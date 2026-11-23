"""Asset library, linking/appending, packing, add-on management, project safety
(checkpoints, undo/redo, execution history), batch processing, workflows, motion tracking."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import Any

from ..utils.objects import get_object, link_object
from . import command, dispatch, history

_DATA_KINDS = {
    "objects": "objects",
    "materials": "materials",
    "meshes": "meshes",
    "collections": "collections",
    "node_groups": "node_groups",
    "worlds": "worlds",
    "actions": "actions",
    "images": "images",
    "brushes": "brushes",
    "scenes": "scenes",
}


def _datablock(kind: str, name: str):
    import bpy

    coll = getattr(bpy.data, _DATA_KINDS.get(kind, kind), None)
    if coll is None:
        raise ValueError(f"Unknown data kind {kind!r}; valid: {sorted(_DATA_KINDS)}")
    block = coll.get(name)
    if block is None:
        raise ValueError(f"{kind} not found: {name}")
    return block


# ------------------------------------------------------------------ asset browser


@command("mark_as_asset")
def mark_as_asset(params: dict[str, Any]):
    kind = params.get("kind") or "objects"
    done = []
    for name in params.get("names") or []:
        block = _datablock(kind, name)
        block.asset_mark()
        with contextlib.suppress(Exception):  # previews need a GPU context
            block.asset_generate_preview()
        meta = block.asset_data
        for tag in params.get("tags") or []:
            if tag not in meta.tags:
                meta.tags.new(tag)
        if params.get("description"):
            meta.description = params["description"]
        if params.get("author") and hasattr(meta, "author"):
            meta.author = params["author"]
        if params.get("catalog_id"):
            meta.catalog_id = params["catalog_id"]
        done.append(block.name)
    return {"marked": done, "kind": kind}


@command("clear_asset")
def clear_asset(params: dict[str, Any]):
    kind = params.get("kind") or "objects"
    done = []
    for name in params.get("names") or []:
        block = _datablock(kind, name)
        block.asset_clear()
        done.append(block.name)
    return {"cleared": done}


@command("tag_asset")
def tag_asset(params: dict[str, Any]):
    block = _datablock(params.get("kind") or "objects", params["name"])
    if block.asset_data is None:
        raise ValueError(f"{block.name} is not marked as an asset")
    tags = block.asset_data.tags
    for t in params.get("add") or []:
        if t not in tags:
            tags.new(t)
    for t in params.get("remove") or []:
        if t in tags:
            tags.remove(tags[t])
    return {"name": block.name, "tags": [t.name for t in tags]}


@command("list_local_assets")
def list_local_assets(params: dict[str, Any]):
    import bpy

    query = (params.get("query") or "").lower()
    out = []
    for kind in _DATA_KINDS.values():
        for block in getattr(bpy.data, kind):
            meta = getattr(block, "asset_data", None)
            if meta is None:
                continue
            tags = [t.name for t in meta.tags]
            hay = " ".join([block.name, meta.description, *tags]).lower()
            if query and query not in hay:
                continue
            out.append(
                {"name": block.name, "kind": kind, "tags": tags, "description": meta.description}
            )
    return out


@command("list_asset_libraries")
def list_asset_libraries(params: dict[str, Any]):
    import bpy

    libs = bpy.context.preferences.filepaths.asset_libraries
    return [{"name": lib.name, "path": lib.path} for lib in libs]


@command("list_blend_contents")
def list_blend_contents(params: dict[str, Any]):
    import bpy

    path = params["path"]
    with bpy.data.libraries.load(path, link=False, assets_only=bool(params.get("assets_only"))) as (
        src,
        _dst,
    ):
        kinds = params.get("kinds") or [
            "objects",
            "collections",
            "materials",
            "node_groups",
            "worlds",
            "actions",
        ]
        return {kind: list(getattr(src, kind, [])) for kind in kinds}


@command("append_from_blend")
def append_from_blend(params: dict[str, Any]):
    """Append (copy) or link (reference) data from another .blend file."""
    import bpy

    path = params["path"]
    kind = params.get("kind") or "objects"
    names = params.get("names") or []
    link = bool(params.get("link", False))
    with bpy.data.libraries.load(path, link=link) as (src, dst):
        available = list(getattr(src, kind))
        wanted = [n for n in names if n in available] if names else available
        missing = [n for n in names if n not in available]
        setattr(dst, kind, wanted)
    loaded = getattr(dst, kind)
    placed = []
    for block in loaded:
        if block is None:
            continue
        if kind == "objects":
            link_object(block, params.get("collection"))
            placed.append(block.name)
        elif kind == "collections":
            if params.get("instance") or link:
                inst = bpy.data.objects.new(block.name, None)
                inst.instance_type, inst.instance_collection = "COLLECTION", block
                link_object(inst, params.get("collection"))
            else:
                bpy.context.scene.collection.children.link(block)
            placed.append(block.name)
        else:
            placed.append(block.name)
    return {"path": path, "kind": kind, "loaded": placed, "missing": missing, "linked": link}


@command("manage_linked_libraries")
def manage_linked_libraries(params: dict[str, Any]):
    """action=list|reload|make_local (``name`` selects a library / object)."""
    import bpy

    action = (params.get("action") or "list").lower()
    if action == "list":
        return [
            {
                "name": lib.name,
                "path": lib.filepath,
                "users": lib.users,
                "missing": not Path(bpy.path.abspath(lib.filepath)).exists(),
            }
            for lib in bpy.data.libraries
        ]
    if action == "reload":
        lib = bpy.data.libraries.get(params["name"])
        if lib is None:
            raise ValueError("library not found")
        lib.reload()
        return {"reloaded": lib.name}
    if action == "make_local":
        obj = get_object(params["name"])
        obj.make_local()
        if obj.data is not None and getattr(obj.data, "library", None):
            obj.data.make_local()
        return {"made_local": obj.name}
    raise ValueError("action must be list, reload or make_local")


@command("pack_resources")
def pack_resources(params: dict[str, Any]):
    import bpy

    action = (params.get("action") or "pack").lower()
    if action == "pack":
        bpy.ops.file.pack_all()
    elif action == "unpack":
        if not params.get("confirmed"):
            raise PermissionError("Unpacking writes files to disk; pass confirmed=true")
        bpy.ops.file.unpack_all(method=(params.get("method") or "USE_LOCAL").upper())
    elif action == "make_relative":
        bpy.ops.file.make_paths_relative()
    elif action == "make_absolute":
        bpy.ops.file.make_paths_absolute()
    else:
        raise ValueError("action must be pack, unpack, make_relative or make_absolute")
    packed = sum(1 for i in bpy.data.images if i.packed_file)
    return {"action": action, "packed_images": packed}


@command("purge_orphans")
def purge_orphans(params: dict[str, Any]):
    import bpy

    if not params.get("confirmed"):
        counts = {
            k: sum(1 for b in getattr(bpy.data, k) if b.users == 0)
            for k in (
                "meshes",
                "materials",
                "images",
                "node_groups",
                "textures",
                "curves",
                "actions",
            )
        }
        return {"preview": counts, "hint": "Pass confirmed=true to delete these unused data-blocks"}
    before = sum(
        len(getattr(bpy.data, k)) for k in ("meshes", "materials", "images", "node_groups")
    )
    bpy.data.orphans_purge(do_recursive=True)
    after = sum(len(getattr(bpy.data, k)) for k in ("meshes", "materials", "images", "node_groups"))
    return {"removed": before - after}


# ------------------------------------------------------------------ add-ons


@command("list_addons")
def list_addons(params: dict[str, Any]):
    import addon_utils

    enabled_only = bool(params.get("enabled_only"))
    query = (params.get("query") or "").lower()
    out = []
    for mod in addon_utils.modules(refresh=False):
        info = addon_utils.module_bl_info(mod)
        is_enabled, _ = addon_utils.check(mod.__name__)
        if enabled_only and not is_enabled:
            continue
        if query and query not in (mod.__name__ + info.get("name", "")).lower():
            continue
        out.append(
            {
                "module": mod.__name__,
                "name": info.get("name"),
                "enabled": is_enabled,
                "version": list(info.get("version", ())),
                "category": info.get("category"),
            }
        )
    return out


@command("set_addon_enabled")
def set_addon_enabled(params: dict[str, Any]):
    import addon_utils
    import bpy

    module = params["module"]
    enable = bool(params.get("enable", True))
    if not enable and not params.get("confirmed"):
        raise PermissionError("Disabling an add-on requires confirmed=true")
    if module.split(".")[0] in {"blender_addon", "blender_mcp_addon"} or "blender_mcp" in module:
        raise PermissionError("Refusing to toggle the MCP bridge add-on from inside itself")
    if enable:
        mod = addon_utils.enable(module, default_set=True, persistent=True)
        if mod is None:
            raise ValueError(f"Could not enable {module}; check list_addons for the module name")
    else:
        addon_utils.disable(module, default_set=True)
    if params.get("save_preferences"):
        bpy.ops.wm.save_userpref()
    return {"module": module, "enabled": addon_utils.check(module)[0]}


# ------------------------------------------------------------------ project safety


def _checkpoint_dir() -> Path:
    import tempfile

    import bpy

    base = Path(bpy.data.filepath).parent if bpy.data.filepath else Path(tempfile.gettempdir())
    d = base / ".mcp_checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


@command("create_checkpoint")
def create_checkpoint(params: dict[str, Any]):
    """Save a timestamped copy of the current file without changing the working file."""
    import bpy

    stem = Path(bpy.data.filepath).stem if bpy.data.filepath else "untitled"
    label = "".join(c for c in (params.get("label") or "checkpoint") if c.isalnum() or c in "-_")[
        :40
    ]
    path = _checkpoint_dir() / f"{stem}_{time.strftime('%Y%m%d-%H%M%S')}_{label}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, compress=True)
    keep = int(params.get("keep") or 20)
    existing = sorted(_checkpoint_dir().glob(f"{stem}_*.blend"), key=lambda p: p.stat().st_mtime)
    for old in existing[:-keep]:
        old.unlink(missing_ok=True)
    return {"checkpoint": str(path), "kept": min(len(existing), keep)}


@command("list_checkpoints")
def list_checkpoints(params: dict[str, Any]):
    files = sorted(_checkpoint_dir().glob("*.blend"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "path": str(p),
            "size_bytes": p.stat().st_size,
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)),
        }
        for p in files
    ]


@command("restore_checkpoint")
def restore_checkpoint(params: dict[str, Any]):
    import bpy

    if not params.get("confirmed"):
        raise PermissionError(
            "Restoring replaces the open file (unsaved work is lost); pass confirmed=true"
        )
    path = Path(params["path"])
    if path.parent.resolve() != _checkpoint_dir().resolve() or not path.exists():
        raise ValueError("path must be a checkpoint from list_checkpoints")
    original = bpy.data.filepath
    bpy.ops.wm.open_mainfile(filepath=str(path))
    if original and params.get("save_over_original"):
        # Continue working under the original file name, now holding the checkpoint state.
        bpy.ops.wm.save_as_mainfile(filepath=original)
    return {"restored": str(path), "working_file": bpy.data.filepath}


def _window_override():
    import bpy

    wm = bpy.context.window_manager
    win = wm.windows[0] if wm.windows else None
    return {"window": win, "screen": win.screen} if win else {}


@command("undo")
def undo(params: dict[str, Any]):
    import bpy

    steps = max(1, min(int(params.get("steps") or 1), 50))
    override = _window_override()
    if not override:
        raise ValueError("Undo needs a Blender window (not available in background mode)")
    done = 0
    with bpy.context.temp_override(**override):
        for _ in range(steps):
            if bpy.ops.ed.undo() != {"FINISHED"}:
                break
            done += 1
    return {"undone": done}


@command("redo")
def redo(params: dict[str, Any]):
    import bpy

    steps = max(1, min(int(params.get("steps") or 1), 50))
    override = _window_override()
    if not override:
        raise ValueError("Redo needs a Blender window")
    done = 0
    with bpy.context.temp_override(**override):
        for _ in range(steps):
            if bpy.ops.ed.redo() != {"FINISHED"}:
                break
            done += 1
    return {"redone": done}


@command("get_undo_history")
def get_undo_history(params: dict[str, Any]):
    import bpy

    wm = bpy.context.window_manager
    steps: list[str] = []
    active = None
    stack = getattr(wm, "undo_stack", None)  # Blender 5.x
    if stack is not None:
        steps = [getattr(st, "name", str(st)) for st in stack.steps]
        active = getattr(stack, "active_index", None)
    elif hasattr(wm, "undo_history"):
        steps = [st.name for st in wm.undo_history]
    limit = int(params.get("limit") or 30)
    return {"undo_steps": steps[-limit:], "active_index": active, "total": len(steps)}


@command("get_execution_history")
def get_execution_history(params: dict[str, Any]):
    limit = int(params.get("limit") or 50)
    items = list(history())
    if params.get("failures_only"):
        items = [i for i in items if not i["success"]]
    return {"history": items[-limit:], "total_recorded": len(items)}


# ------------------------------------------------------------------ batch & workflow

_BLOCKED_IN_BATCH = {
    "execute_blender_code",
    "execute_python",
    "run_workflow",
    "batch_apply",
    "restore_checkpoint",
    "open_blend_file",
    "new_blend_file",
    "revert_blend_file",
    "set_addon_enabled",
}


def _select(params: dict[str, Any]):
    import fnmatch

    import bpy

    names = params.get("objects")
    if names:
        return [get_object(n) for n in names]
    pattern = params.get("pattern") or "*"
    otype = (params.get("object_type") or "").upper()
    coll = bpy.data.collections.get(params.get("collection") or "")
    pool = coll.all_objects if coll else bpy.context.scene.objects
    return [o for o in pool if fnmatch.fnmatch(o.name, pattern) and (not otype or o.type == otype)]


@command("batch_apply")
def batch_apply(params: dict[str, Any]):
    """Run one command for every matching object; ``name_param`` receives each object name."""
    cmd = params["command"]
    if cmd in _BLOCKED_IN_BATCH:
        raise PermissionError(f"{cmd} cannot be batched")
    key = params.get("name_param") or "name"
    results = []
    for obj in _select(params):
        res = dispatch(cmd, {**(params.get("params") or {}), key: obj.name})
        results.append(
            {"object": obj.name, "success": res.get("success"), "error": res.get("error")}
        )
        if not res.get("success") and params.get("stop_on_error"):
            break
    return {
        "command": cmd,
        "processed": len(results),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results,
    }


@command("batch_rename")
def batch_rename(params: dict[str, Any]):
    objs = _select(params)
    find, replace = params.get("find"), params.get("replace") or ""
    prefix, suffix = params.get("prefix") or "", params.get("suffix") or ""
    numbered = params.get("numbered_base")
    renamed = []
    for i, obj in enumerate(sorted(objs, key=lambda o: o.name), 1):
        old = obj.name
        new = f"{numbered}_{i:03d}" if numbered else (old.replace(find, replace) if find else old)
        obj.name = f"{prefix}{new}{suffix}"
        if params.get("rename_data") and obj.data is not None:
            obj.data.name = obj.name
        renamed.append([old, obj.name])
    return {"renamed": renamed}


@command("batch_export")
def batch_export(params: dict[str, Any]):
    """Export each matching object to its own file in ``directory``."""
    from .import_export import export_asset

    directory = Path(params["directory"]).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    fmt = (params.get("format") or "glb").lower().lstrip(".")
    out = []
    for obj in _select(params):
        path = directory / f"{obj.name}.{fmt}"
        try:
            export_asset(
                {
                    "path": str(path),
                    "objects": [obj.name],
                    "overwrite": bool(params.get("overwrite")),
                }
            )
            out.append({"object": obj.name, "path": str(path)})
        except Exception as exc:  # noqa: BLE001
            out.append({"object": obj.name, "error": str(exc)})
    return {"exported": out}


@command("run_workflow")
def run_workflow(params: dict[str, Any]):
    """Execute an ordered plan ``steps=[{command, params, label?}]`` with an optional checkpoint
    first. Each step's result is reported; ``stop_on_error`` (default true) halts the plan."""
    steps = params.get("steps") or []
    if not steps:
        raise ValueError("steps is required")
    if len(steps) > 200:
        raise ValueError("A workflow is limited to 200 steps")
    report: dict[str, Any] = {"steps": []}
    if params.get("checkpoint", True):
        try:
            report["checkpoint"] = create_checkpoint(
                {"label": params.get("label") or "before_workflow"}
            )["checkpoint"]
        except Exception as exc:  # noqa: BLE001
            report["checkpoint_error"] = str(exc)
    for i, step in enumerate(steps):
        cmd = step.get("command")
        if cmd in _BLOCKED_IN_BATCH:
            res = {"success": False, "error": f"{cmd} is not allowed inside run_workflow"}
        else:
            t0 = time.perf_counter()
            res = dispatch(cmd, step.get("params") or {})
            res["seconds"] = round(time.perf_counter() - t0, 3)
        entry = {
            "index": i,
            "label": step.get("label"),
            "command": cmd,
            "success": res.get("success"),
            "result": res.get("result") if params.get("verbose") else None,
            "error": res.get("error"),
        }
        report["steps"].append(entry)
        if not res.get("success") and params.get("stop_on_error", True):
            report["stopped_at"] = i
            break
    report["succeeded"] = sum(1 for s in report["steps"] if s["success"])
    report["failed"] = sum(1 for s in report["steps"] if not s["success"])
    return report


# ------------------------------------------------------------------ motion tracking


@command("load_movie_clip")
def load_movie_clip(params: dict[str, Any]):
    import bpy

    clip = bpy.data.movieclips.load(params["path"], check_existing=True)
    scene = bpy.context.scene
    scene.active_clip = clip
    if params.get("set_scene_range", True):
        scene.frame_start = clip.frame_start
        scene.frame_end = clip.frame_start + clip.frame_duration - 1
    if params.get("sensor_width"):
        clip.tracking.camera.sensor_width = float(params["sensor_width"])
    if params.get("focal_length"):
        clip.tracking.camera.focal_length = float(params["focal_length"])
    return {
        "clip": clip.name,
        "frames": clip.frame_duration,
        "size": list(clip.size),
        "fps": clip.fps,
    }


def _clip_override(clip):
    import bpy

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "CLIP_EDITOR":
                area.spaces.active.clip = clip
                region = next(r for r in area.regions if r.type == "WINDOW")
                return {
                    "window": window,
                    "screen": window.screen,
                    "area": area,
                    "region": region,
                    "edit_movieclip": clip,
                }
    # Borrow the largest area as a temporary clip editor.
    window = bpy.context.window_manager.windows[0]
    area = max(window.screen.areas, key=lambda a: a.width * a.height)
    area.type = "CLIP_EDITOR"
    area.spaces.active.clip = clip
    region = next(r for r in area.regions if r.type == "WINDOW")
    return {
        "window": window,
        "screen": window.screen,
        "area": area,
        "region": region,
        "edit_movieclip": clip,
    }


@command("track_camera_motion")
def track_camera_motion(params: dict[str, Any]):
    """Detect features, track them through the clip, solve the camera and set up the scene."""
    import bpy

    clip = bpy.data.movieclips.get(params["clip"])
    if clip is None:
        raise ValueError("clip not found; use load_movie_clip first")
    if not bpy.context.window_manager.windows:
        raise ValueError("Motion tracking needs the Blender UI (not available in background mode)")
    override = _clip_override(clip)
    scene = bpy.context.scene
    with bpy.context.temp_override(**override):
        scene.frame_set(clip.frame_start)
        bpy.ops.clip.detect_features(
            threshold=float(params.get("threshold") or 0.3),
            min_distance=int(params.get("min_distance") or 120),
        )
        bpy.ops.clip.track_markers(backwards=False, sequence=True)
        bpy.ops.clip.solve_camera()
        if params.get("setup_scene", True):
            bpy.ops.clip.setup_tracking_scene()
    tracking = clip.tracking
    return {
        "clip": clip.name,
        "tracks": len(tracking.tracks),
        "solve_error": tracking.reconstruction.average_error
        if tracking.reconstruction.is_valid
        else None,
        "valid": tracking.reconstruction.is_valid,
    }


@command("get_tracking_info")
def get_tracking_info(params: dict[str, Any]):
    import bpy

    clip = bpy.data.movieclips.get(params["clip"])
    if clip is None:
        raise ValueError("clip not found")
    t = clip.tracking
    return {
        "clip": clip.name,
        "tracks": [tr.name for tr in t.tracks][:200],
        "track_count": len(t.tracks),
        "solved": t.reconstruction.is_valid,
        "solve_error": t.reconstruction.average_error if t.reconstruction.is_valid else None,
        "camera": {"focal_length": t.camera.focal_length, "sensor_width": t.camera.sensor_width},
    }
