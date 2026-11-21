"""Import/export and project file handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import command


def _ext(path: str) -> str:
    return Path(path).suffix.lower()


@command("import_asset")
def import_asset(params: dict[str, Any]):
    import bpy

    path = Path(params["path"]).expanduser()
    if not path.exists():
        raise ValueError(f"File not found: {path}")
    ext = path.suffix.lower()
    before = set(bpy.data.objects.keys())
    if ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(path))
        else:
            bpy.ops.import_scene.obj(filepath=str(path))
    elif ext == ".stl":
        if hasattr(bpy.ops.wm, "stl_import"):
            bpy.ops.wm.stl_import(filepath=str(path))
        else:
            bpy.ops.import_mesh.stl(filepath=str(path))
    elif ext in {".usd", ".usda", ".usdc", ".usdz"}:
        bpy.ops.wm.usd_import(filepath=str(path))
    elif ext == ".blend":
        with bpy.data.libraries.load(str(path)) as (data_from, data_to):
            data_to.objects = data_from.objects
        for obj in data_to.objects:
            if obj is not None:
                bpy.context.scene.collection.objects.link(obj)
    else:
        raise ValueError(f"Unsupported import format: {ext}")
    imported = sorted(set(bpy.data.objects.keys()) - before)
    if params.get("collection"):
        from .collections import move_object_to_collection

        for name in imported:
            move_object_to_collection(
                {"object_name": name, "collection": params["collection"], "exclusive": True}
            )
    return {"imported_objects": imported, "path": str(path)}


@command("export_asset")
@command("export_selected_objects")
@command("export_scene")
def export_asset(params: dict[str, Any]):
    import bpy

    path = Path(params["path"]).expanduser()
    if path.exists() and not params.get("overwrite", False):
        raise PermissionError(f"Refusing to overwrite existing file without overwrite=true: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    objects = params.get("objects")
    if objects:
        bpy.ops.object.select_all(action="DESELECT")
        for name in objects:
            obj = bpy.data.objects.get(name)
            if obj:
                obj.select_set(True)
    use_selection = bool(objects) or params.get("selected_only", False)
    if ext in {".glb", ".gltf"}:
        bpy.ops.export_scene.gltf(filepath=str(path), use_selection=use_selection)
    elif ext == ".fbx":
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=use_selection)
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_export"):
            bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=use_selection)
        else:
            bpy.ops.export_scene.obj(filepath=str(path), use_selection=use_selection)
    elif ext == ".stl":
        if hasattr(bpy.ops.wm, "stl_export"):
            bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=use_selection)
        else:
            bpy.ops.export_mesh.stl(filepath=str(path), use_selection=use_selection)
    elif ext in {".usd", ".usda", ".usdc"}:
        bpy.ops.wm.usd_export(filepath=str(path), selected_objects_only=use_selection)
    else:
        raise ValueError(f"Unsupported export format: {ext}")
    return {"path": str(path), "exported": True}


@command("save_blend_file")
@command("save_as")
def save_blend_file(params: dict[str, Any]):
    import bpy

    path = params.get("path") or bpy.data.filepath
    if not path:
        raise ValueError("No path provided and current file is unsaved")
    path_obj = Path(path).expanduser()
    if path_obj.exists() and not params.get("overwrite", True):
        raise PermissionError("Refusing to overwrite without overwrite=true")
    bpy.ops.wm.save_as_mainfile(filepath=str(path_obj))
    return {"path": bpy.data.filepath}


@command("open_blend_file")
def open_blend_file(params: dict[str, Any]):
    import bpy

    if params.get("check_unsaved"):
        _guard_unsaved(params)
    path = Path(params["path"]).expanduser()
    if not path.exists():
        raise ValueError(f"File not found: {path}")
    bpy.ops.wm.open_mainfile(filepath=str(path))
    return {"path": bpy.data.filepath}


@command("get_project_path")
def get_project_path(params: dict[str, Any]):
    import bpy

    return {"path": bpy.data.filepath or None, "unsaved": not bool(bpy.data.filepath)}


def _blend_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if path.suffix.lower() != ".blend":
        path = path.with_name(path.name + ".blend")
    return path


def _guard_unsaved(params: dict[str, Any]) -> None:
    from ..unsaved import has_unsaved_changes

    if has_unsaved_changes() and not params.get("discard_changes", False):
        raise ValueError(
            "The open file has unsaved changes; save first or pass discard_changes=true"
        )


@command("blend_file_info")
def blend_file_info(params: dict[str, Any]):
    import bpy

    from ..unsaved import has_unsaved_changes

    path = bpy.data.filepath
    return {
        "path": path or None,
        "name": Path(path).name if path else None,
        "saved_once": bool(path),
        "unsaved_changes": has_unsaved_changes(),
    }


@command("save_copy")
def save_copy(params: dict[str, Any]):
    import bpy

    path = _blend_path(params["path"])
    if path.exists() and not params.get("overwrite", False):
        raise PermissionError(f"{path} exists; pass overwrite=true to replace it")
    from ..unsaved import has_unsaved_changes, mark

    path.parent.mkdir(parents=True, exist_ok=True)
    changed = has_unsaved_changes()
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True)
    mark(changed)  # a copy does not save the open file
    return {"copy": str(path), "current": bpy.data.filepath}


@command("rename_blend_file")
def rename_blend_file(params: dict[str, Any]):
    """Rename the open .blend on disk; ``new_name`` is a name or a full path."""
    import bpy

    old = bpy.data.filepath
    if not old:
        raise ValueError("The file has never been saved; use save_as instead")
    old_path = Path(old)
    raw = params["new_name"]
    new_path = _blend_path(raw if ("/" in raw or "\\" in raw) else str(old_path.parent / raw))
    if new_path.resolve() == old_path.resolve():
        return {"path": old, "renamed": False}
    if new_path.exists():
        raise PermissionError(f"{new_path} already exists")
    new_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(new_path))
    result = {"old_path": old, "path": bpy.data.filepath, "renamed": True}
    stale = [p for p in (old_path, old_path.with_name(old_path.name + "1")) if p.exists()]
    if params.get("keep_old", False):
        result["kept"] = [str(p) for p in stale]
        return result

    from ..utils.trash import move_to_trash

    # Trash, never delete: the user can restore the old file if the rename was a mistake.
    result["trashed"] = [str(p) for p in stale if move_to_trash(p)]
    result["kept"] = [str(p) for p in stale if p.exists()]
    if result["kept"]:
        result["warning"] = "Could not move the old file to the trash; it was left in place"
    return result


@command("new_blend_file")
def new_blend_file(params: dict[str, Any]):
    import bpy

    _guard_unsaved(params)
    bpy.ops.wm.read_homefile(use_empty=bool(params.get("empty", False)))
    return {"path": None, "new": True}


@command("revert_blend_file")
def revert_blend_file(params: dict[str, Any]):
    import bpy

    if not bpy.data.filepath:
        raise ValueError("The file has never been saved; nothing to revert to")
    bpy.ops.wm.revert_mainfile()
    return {"path": bpy.data.filepath, "reverted": True}


@command("list_blend_files")
def list_blend_files(params: dict[str, Any]):
    import bpy

    directory = params.get("directory") or (
        str(Path(bpy.data.filepath).parent) if bpy.data.filepath else ""
    )
    if not directory:
        raise ValueError("No directory given and the open file has never been saved")
    root = Path(directory).expanduser()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    files = sorted(root.glob("**/*.blend" if params.get("recursive") else "*.blend"))
    limit = int(params.get("limit", 100))
    return {
        "directory": str(root),
        "files": [
            {"path": str(p), "size_bytes": p.stat().st_size, "modified": p.stat().st_mtime}
            for p in files[:limit]
        ],
        "truncated": len(files) > limit,
    }


def _file_entry(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {"path": str(path), "size_bytes": stat.st_size, "modified": stat.st_mtime}


@command("recent_blend_files")
def recent_blend_files(params: dict[str, Any]):
    """Blender's File > Open Recent list, newest first."""
    import bpy

    config = bpy.utils.user_resource("CONFIG")
    listing = Path(config) / "recent-files.txt"
    limit = int(params.get("limit", 20))
    files = []
    if listing.is_file():
        for line in listing.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            path = Path(line)
            files.append(_file_entry(path) if path.is_file() else {"path": line, "missing": True})
            if len(files) >= limit:
                break
    return {"files": files, "source": str(listing)}


def _temp_dir() -> Path:
    import bpy

    prefs = bpy.context.preferences.filepaths
    configured = getattr(prefs, "temporary_directory", "")
    return Path(configured) if configured else Path(bpy.app.tempdir).parent


@command("list_autosaves")
def list_autosaves(params: dict[str, Any]):
    """Autosaves and the last-session file (quit.blend), newest first."""
    root = _temp_dir()
    found = [p for p in root.glob("*.blend") if p.name == "quit.blend" or "autosave" in p.name]
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    entries = []
    for p in found:
        entry = _file_entry(p)
        entry["kind"] = "last_session" if p.name == "quit.blend" else "autosave"
        entries.append(entry)
    return {"directory": str(root), "files": entries}


@command("recover_blend_file")
def recover_blend_file(params: dict[str, Any]):
    """Open an autosave, or the last session (quit.blend) when no path is given.

    Blender keeps the last session's original path, so a plain save writes over that
    file. An autosave keeps its temp-folder path, so it should be saved with save_as.
    """
    import bpy

    _guard_unsaved(params)
    raw = params.get("path")
    if not raw:
        quit_file = _temp_dir() / "quit.blend"
        if not quit_file.is_file():
            raise ValueError(f"No last-session file found at {quit_file}")
        bpy.ops.wm.recover_last_session()
        path = bpy.data.filepath
        return {
            "recovered": str(quit_file),
            "kind": "last_session",
            "path": path or None,
            "note": f"Saving now writes over {path}" if path else "Save it with save_as",
        }
    path = Path(raw).expanduser()
    if not path.is_file():
        raise ValueError(f"File not found: {path}")
    if path.resolve().parent != _temp_dir().resolve():
        raise PermissionError("Only autosaves from Blender's temporary folder can be recovered")
    bpy.ops.wm.recover_auto_save(filepath=str(path))
    return {
        "recovered": str(path),
        "kind": "autosave",
        "path": bpy.data.filepath or None,
        "note": "This file points at the autosave in the temporary folder; "
        "save it with save_as to keep it",
    }
