"""Addon file commands (save, rename, new, quit) against a fake ``bpy``."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


class FakeBpy:
    """Just enough of ``bpy`` for the file commands: real files, fake Blender."""

    def __init__(self) -> None:
        self.data = types.SimpleNamespace(filepath="", is_dirty=False)
        self.handlers = types.SimpleNamespace(
            depsgraph_update_post=[], save_post=[], load_post=[], persistent=lambda f: f
        )
        self.timers: list[Any] = []
        self.calls: list[str] = []
        wm = types.SimpleNamespace(
            save_as_mainfile=self._save_as,
            save_mainfile=lambda: self._save_as(self.data.filepath),
            read_homefile=self._read_homefile,
            revert_mainfile=lambda: self._fire("load_post"),
            quit_blender=lambda: self.calls.append("quit"),
        )
        self.ops = types.SimpleNamespace(wm=wm)
        self.app = types.SimpleNamespace(
            handlers=self.handlers,
            timers=types.SimpleNamespace(register=lambda fn, **_: self.timers.append(fn)),
        )

    def _fire(self, name: str) -> None:
        for fn in list(getattr(self.handlers, name)):
            fn(None)

    def _save_as(self, filepath: str, copy: bool = False) -> None:
        Path(filepath).write_bytes(b"BLENDER")
        if not copy:
            self.data.filepath = filepath
            self.data.is_dirty = False
        self._fire("save_post")

    def _read_homefile(self, use_empty: bool = False) -> None:
        self.data.filepath = ""
        self._fire("load_post")

    def edit_scene(self) -> None:
        """A script edit: the depsgraph updates but is_dirty stays False."""
        self._fire("depsgraph_update_post")


@pytest.fixture
def addon(monkeypatch):
    bpy = FakeBpy()
    monkeypatch.setitem(sys.modules, "bpy", bpy)
    persistent_mod = types.ModuleType("bpy.app.handlers")
    persistent_mod.persistent = lambda f: f
    monkeypatch.setitem(sys.modules, "bpy.app", types.ModuleType("bpy.app"))
    monkeypatch.setitem(sys.modules, "bpy.app.handlers", persistent_mod)
    if "blender_addon" not in sys.modules:
        pkg = types.ModuleType("blender_addon")
        pkg.__path__ = [str(ROOT / "blender_addon")]
        monkeypatch.setitem(sys.modules, "blender_addon", pkg)
    unsaved = importlib.import_module("blender_addon.unsaved")
    io = importlib.import_module("blender_addon.handlers.import_export")
    diag = importlib.import_module("blender_addon.handlers.diagnostics")
    trash = importlib.import_module("blender_addon.utils.trash")
    trashed: list[Path] = []

    def fake_trash(path):
        trashed.append(Path(path))
        Path(path).unlink()
        return True

    monkeypatch.setattr(trash, "move_to_trash", fake_trash)
    unsaved.mark(False)
    unsaved.register()
    return types.SimpleNamespace(bpy=bpy, io=io, diag=diag, unsaved=unsaved, trashed=trashed)


def test_script_edits_count_as_unsaved(addon, tmp_path):
    addon.io.save_blend_file({"path": str(tmp_path / "a.blend"), "overwrite": True})
    assert addon.io.blend_file_info({})["unsaved_changes"] is False
    addon.bpy.edit_scene()
    assert addon.io.blend_file_info({})["unsaved_changes"] is True
    addon.io.save_blend_file({})
    assert addon.io.blend_file_info({})["unsaved_changes"] is False


def test_new_refuses_unsaved_unless_discarded(addon):
    addon.bpy.edit_scene()
    with pytest.raises(ValueError, match="unsaved"):
        addon.io.new_blend_file({})
    assert addon.io.new_blend_file({"discard_changes": True})["new"] is True


def test_save_copy_keeps_unsaved_state(addon, tmp_path):
    addon.io.save_blend_file({"path": str(tmp_path / "a.blend"), "overwrite": True})
    addon.bpy.edit_scene()
    result = addon.io.save_copy({"path": str(tmp_path / "copy")})
    assert result["copy"].endswith("copy.blend")
    assert Path(result["copy"]).exists()
    assert addon.bpy.data.filepath.endswith("a.blend")
    assert addon.io.blend_file_info({})["unsaved_changes"] is True


def test_save_copy_refuses_overwrite(addon, tmp_path):
    (tmp_path / "copy.blend").write_bytes(b"x")
    with pytest.raises(PermissionError):
        addon.io.save_copy({"path": str(tmp_path / "copy.blend")})


def test_rename_moves_file_and_backup(addon, tmp_path):
    addon.io.save_blend_file({"path": str(tmp_path / "first.blend"), "overwrite": True})
    (tmp_path / "first.blend1").write_bytes(b"backup")
    result = addon.io.rename_blend_file({"new_name": "second"})
    assert result["renamed"] is True
    assert Path(result["path"]).name == "second.blend"
    assert sorted(p.name for p in addon.trashed) == ["first.blend", "first.blend1"]
    assert result["kept"] == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["second.blend"]


def test_rename_keep_old_leaves_file(addon, tmp_path):
    addon.io.save_blend_file({"path": str(tmp_path / "first.blend"), "overwrite": True})
    result = addon.io.rename_blend_file({"new_name": "second", "keep_old": True})
    assert addon.trashed == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["first.blend", "second.blend"]
    assert result["kept"] == [str(tmp_path / "first.blend")]


def test_rename_keeps_old_file_when_trash_fails(addon, tmp_path, monkeypatch):
    trash = importlib.import_module("blender_addon.utils.trash")
    monkeypatch.setattr(trash, "move_to_trash", lambda path: False)
    addon.io.save_blend_file({"path": str(tmp_path / "first.blend"), "overwrite": True})
    result = addon.io.rename_blend_file({"new_name": "second"})
    assert (tmp_path / "first.blend").exists()
    assert "warning" in result


def test_rename_refuses_existing_target_and_unsaved_file(addon, tmp_path):
    with pytest.raises(ValueError, match="never been saved"):
        addon.io.rename_blend_file({"new_name": "x"})
    addon.io.save_blend_file({"path": str(tmp_path / "first.blend"), "overwrite": True})
    (tmp_path / "taken.blend").write_bytes(b"x")
    with pytest.raises(PermissionError):
        addon.io.rename_blend_file({"new_name": "taken"})
    assert (tmp_path / "first.blend").exists()


def test_rename_to_same_name_is_noop(addon, tmp_path):
    addon.io.save_blend_file({"path": str(tmp_path / "first.blend"), "overwrite": True})
    assert addon.io.rename_blend_file({"new_name": "first"})["renamed"] is False


def test_list_blend_files(addon, tmp_path):
    (tmp_path / "a.blend").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.blend").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("x")
    flat = addon.io.list_blend_files({"directory": str(tmp_path)})
    deep = addon.io.list_blend_files({"directory": str(tmp_path), "recursive": True})
    assert [Path(f["path"]).name for f in flat["files"]] == ["a.blend"]
    assert len(deep["files"]) == 2


def test_quit_refuses_unsaved_then_quits_after_reply(addon, tmp_path):
    addon.bpy.edit_scene()
    with pytest.raises(ValueError, match="unsaved"):
        addon.diag.quit_blender({})
    assert addon.diag.quit_blender({"discard_changes": True})["quitting"] is True
    assert addon.bpy.calls == []  # deferred until the timer runs
    addon.bpy.timers[0]()
    assert addon.bpy.calls == ["quit"]


def test_quit_with_save_needs_a_saved_file(addon):
    with pytest.raises(ValueError, match="never been saved"):
        addon.diag.quit_blender({"save": True})


def test_unsaved_register_does_not_duplicate(addon):
    addon.unsaved.register()
    addon.unsaved.register()
    names = [f.__name__ for f in addon.bpy.handlers.depsgraph_update_post]
    assert names.count("_on_change") == 1


# --- recent files, autosaves, recovery ----------------------------------------------


@pytest.fixture
def dirs(addon, tmp_path):
    """Give the fake bpy a config folder and a temp folder, plus recovery operators."""
    config, temp = tmp_path / "config", tmp_path / "temp"
    config.mkdir()
    temp.mkdir()
    bpy = addon.bpy
    bpy.utils = types.SimpleNamespace(user_resource=lambda kind: str(config))
    bpy.context = types.SimpleNamespace(
        preferences=types.SimpleNamespace(
            filepaths=types.SimpleNamespace(temporary_directory=str(temp))
        )
    )
    bpy.app.tempdir = str(temp / "blender_1234")
    bpy.ops.wm.recover_last_session = lambda: bpy.calls.append("recover_last_session")
    bpy.ops.wm.recover_auto_save = lambda filepath: bpy.calls.append(f"recover:{filepath}")
    return config, temp


def test_recent_files_reads_blender_list(addon, dirs, tmp_path):
    config, _ = dirs
    there = tmp_path / "there.blend"
    there.write_bytes(b"x")
    gone = tmp_path / "gone.blend"
    (config / "recent-files.txt").write_text(f"{there}\n\n{gone}\n")
    files = addon.io.recent_blend_files({})["files"]
    assert files[0]["path"] == str(there) and "size_bytes" in files[0]
    assert files[1] == {"path": str(gone), "missing": True}
    assert len(addon.io.recent_blend_files({"limit": 1})["files"]) == 1


def test_recent_files_without_list(addon, dirs):
    assert addon.io.recent_blend_files({})["files"] == []


def test_list_autosaves_finds_autosave_and_quit(addon, dirs):
    _, temp = dirs
    for name in ("scene_1234_autosave.blend", "quit.blend", "other.blend"):
        (temp / name).write_bytes(b"x")
    kinds = {Path(f["path"]).name: f["kind"] for f in addon.io.list_autosaves({})["files"]}
    assert kinds == {"scene_1234_autosave.blend": "autosave", "quit.blend": "last_session"}


def test_recover_last_session(addon, dirs):
    _, temp = dirs
    with pytest.raises(ValueError, match="No last-session"):
        addon.io.recover_blend_file({})
    (temp / "quit.blend").write_bytes(b"x")
    assert addon.io.recover_blend_file({})["kind"] == "last_session"
    assert addon.bpy.calls == ["recover_last_session"]


def test_recover_autosave_only_from_temp_folder(addon, dirs, tmp_path):
    _, temp = dirs
    auto = temp / "scene_autosave.blend"
    auto.write_bytes(b"x")
    outside = tmp_path / "elsewhere.blend"
    outside.write_bytes(b"x")
    with pytest.raises(PermissionError):
        addon.io.recover_blend_file({"path": str(outside)})
    assert addon.io.recover_blend_file({"path": str(auto)})["kind"] == "autosave"
    assert addon.bpy.calls == [f"recover:{auto}"]


def test_recover_refuses_unsaved_changes(addon, dirs):
    _, temp = dirs
    (temp / "quit.blend").write_bytes(b"x")
    addon.bpy.edit_scene()
    with pytest.raises(ValueError, match="unsaved"):
        addon.io.recover_blend_file({})
    assert addon.io.recover_blend_file({"discard_changes": True})["kind"] == "last_session"
