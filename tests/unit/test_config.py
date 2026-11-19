from blender_mcp.config import ScriptPermission, load_settings


def test_default_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = load_settings(tmp_path / "missing.toml")
    assert settings.host == "127.0.0.1"
    assert settings.port == 9876
    assert settings.script_permission == ScriptPermission.RESTRICTED
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
