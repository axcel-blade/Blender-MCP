"""Trash helper (addon) and Blender install/version discovery (server)."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

from blender_mcp.tools import app

ROOT = Path(__file__).resolve().parents[2]


def _trash_module():
    if "blender_addon" not in sys.modules:
        pkg = types.ModuleType("blender_addon")
        pkg.__path__ = [str(ROOT / "blender_addon")]
        sys.modules["blender_addon"] = pkg
    return importlib.import_module("blender_addon.utils.trash")


def test_freedesktop_trash_moves_file_and_writes_info(tmp_path, monkeypatch):
    trash = _trash_module()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    f = tmp_path / "old.blend"
    f.write_bytes(b"x")
    assert trash._freedesktop(f) is True  # noqa: SLF001
    assert not f.exists()
    base = tmp_path / "data" / "Trash"
    assert (base / "files" / "old.blend").exists()
    assert "Path=" in (base / "info" / "old.blend.trashinfo").read_text()


def test_trash_names_do_not_collide(tmp_path, monkeypatch):
    trash = _trash_module()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    for _ in range(2):
        f = tmp_path / "old.blend"
        f.write_bytes(b"x")
        trash._freedesktop(f)  # noqa: SLF001
    names = sorted(p.name for p in (tmp_path / "data" / "Trash" / "files").iterdir())
    assert names == ["old 2.blend", "old.blend"]


def test_move_to_trash_missing_file_is_false(tmp_path):
    assert _trash_module().move_to_trash(tmp_path / "nope.blend") is False


def test_version_from_folder_name():
    exe = r"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
    assert app.blender_version(exe) == "5.3"


def test_version_falls_back_to_executable(monkeypatch):
    monkeypatch.setattr(app, "_version_from_executable", lambda exe: "5.2.1")
    exe = r"C:\Steam\steamapps\common\Blender\blender.exe"
    assert app.blender_version(exe) == "5.2.1"


def test_find_blender_picks_newest_or_requested(monkeypatch):
    installs = [
        {"path": "b53", "version": "5.3", "source": "install folder"},
        {"path": "b52", "version": "5.2.1", "source": "Steam"},
        {"path": "unknown", "version": None, "source": "PATH"},
    ]
    monkeypatch.setattr(app, "list_installs", lambda: installs)
    assert app.find_blender() == "b53"
    assert app.find_blender(version="5.2") == "b52"
    assert app.find_blender(version="5.2.1") == "b52"
    assert app.find_blender(version="4.5") is None


def test_list_installs_sorts_and_dedupes(tmp_path, monkeypatch):
    old = tmp_path / "Blender 4.5" / "blender.exe"
    new = tmp_path / "Blender 5.3" / "blender.exe"
    for exe in (old, new):
        exe.parent.mkdir()
        exe.write_bytes(b"")
    monkeypatch.setattr(app.shutil, "which", lambda name: str(new))
    monkeypatch.setattr(app, "_candidate_paths", lambda: [str(old), str(new)])
    found = app.list_installs()
    assert [i["version"] for i in found] == ["5.3", "4.5"]
    assert found[0]["source"] == "PATH"
