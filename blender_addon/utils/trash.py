"""Move files to the system trash (Recycle Bin, macOS Trash, freedesktop Trash)."""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import quote


def _unique(target: Path) -> Path:
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    n = 2
    while (candidate := target.with_name(f"{stem} {n}{suffix}")).exists():
        n += 1
    return candidate


def _windows(path: Path) -> bool:
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_uint16),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    FO_DELETE = 3
    FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 0x4, 0x10, 0x40, 0x400
    op = SHFILEOPSTRUCTW(
        wFunc=FO_DELETE,
        pFrom=str(path) + "\0",  # list is double-NUL terminated
        fFlags=FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI,
    )
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not path.exists()


def _macos(path: Path) -> bool:
    trash = Path.home() / ".Trash"
    if not trash.is_dir():
        return False
    shutil.move(str(path), str(_unique(trash / path.name)))
    return True


def _freedesktop(path: Path) -> bool:
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "Trash"
    files, info = base / "files", base / "info"
    files.mkdir(parents=True, exist_ok=True)
    info.mkdir(parents=True, exist_ok=True)
    target = _unique(files / path.name)
    (info / f"{target.name}.trashinfo").write_text(
        "[Trash Info]\n"
        f"Path={quote(str(path.resolve()))}\n"
        f"DeletionDate={time.strftime('%Y-%m-%dT%H:%M:%S')}\n",
        encoding="utf-8",
    )
    shutil.move(str(path), str(target))
    return True


def move_to_trash(path: str | Path) -> bool:
    """Trash ``path``. Returns False (file left in place) when that is not possible."""
    path = Path(path)
    if not path.exists():
        return False
    try:
        if sys.platform == "win32":
            return _windows(path)
        if sys.platform == "darwin":
            return _macos(path)
        return _freedesktop(path)
    except Exception:  # noqa: BLE001
        return False
