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

    path = Path(params["path"]).expanduser()
    if not path.exists():
        raise ValueError(f"File not found: {path}")
    bpy.ops.wm.open_mainfile(filepath=str(path))
    return {"path": bpy.data.filepath}


@command("get_project_path")
def get_project_path(params: dict[str, Any]):
    import bpy

    return {"path": bpy.data.filepath or None, "unsaved": not bool(bpy.data.filepath)}
