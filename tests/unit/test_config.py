from blender_mcp.config import ScriptPermission, load_settings


def test_default_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = load_settings(tmp_path / "missing.toml")
    assert settings.host == "127.0.0.1"
    assert settings.port == 9877
    assert settings.script_permission == ScriptPermission.TRUSTED
    assert settings.tool_groups.scene is True


def test_toml_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        """
[bridge]
host = "10.0.0.2"
port = 9999

[security]
script_permission = "trusted"
""",
        encoding="utf-8",
    )
    settings = load_settings(cfg)
    assert settings.host == "10.0.0.2"
    assert settings.port == 9999
    assert settings.script_permission == ScriptPermission.TRUSTED


def test_toml_blender_section(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('[blender]\npath = "C:/Blender/blender.exe"\nlaunch_timeout = 90\n')
    settings = load_settings(cfg)
    assert settings.blender_path == "C:/Blender/blender.exe"
    assert settings.blender_launch_timeout == 90


def test_example_config_loads():
    from pathlib import Path

    settings = load_settings(Path(__file__).parents[2] / "config.example.toml")
    assert settings.blender_path == ""
    assert settings.blender_launch_timeout == 60
