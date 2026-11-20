import io
import sys

from blender_mcp import cli


def test_console_output_safe_on_legacy_codepage(monkeypatch, capsys):
    """Non-ASCII text must not crash on a cp1252 console (Windows default)."""
    fake = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", fake)
    cli._make_console_output_safe()
    print("Edit → Preferences → Add-ons")
    fake.flush()
    assert fake.buffer.getvalue().startswith(b"Edit ? Preferences")
