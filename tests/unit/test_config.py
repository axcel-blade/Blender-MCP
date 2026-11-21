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


def test_env_overrides_toml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[bridge]\nport = 1111\nhost = "10.0.0.2"\n[blender]\nlaunch_timeout = 11\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("BLENDER_MCP_PORT", "2222")
    monkeypatch.setenv("BLENDER_MCP_BLENDER_LAUNCH_TIMEOUT", "22")
    monkeypatch.setenv("BLENDER_MCP_SCRIPT_PERMISSION", "confirmation")
    settings = load_settings(cfg)
    assert settings.port == 2222  # env beats TOML
    assert settings.blender_launch_timeout == 22
    assert settings.host == "10.0.0.2"  # TOML still beats defaults
    # Not in the TOML at all: the loader's fallback default must not hide the env value.
    assert settings.script_permission == ScriptPermission.CONFIRMATION


def test_dotenv_overrides_toml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("BLENDER_MCP_PORT=3333\n", encoding="utf-8")
    cfg = tmp_path / "config.toml"
    cfg.write_text("[bridge]\nport = 1111\n", encoding="utf-8")
    assert load_settings(cfg).port == 3333


def test_only_prefixed_env_vars_are_read(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Generic names other tools set must not change the bridge.
    for name, value in {
        "PORT": "3333",
        "HOST": "1.2.3.4",
        "LOG_LEVEL": "DEBUG",
        "AUTH_TOKEN": "x",
        "SAFE_EXECUTION": "false",
        "SAFE_EXECUTION_MODE": "false",
    }.items():
        monkeypatch.setenv(name, value)
    settings = load_settings(tmp_path / "missing.toml")
    assert settings.port == 9877
    assert settings.host == "127.0.0.1"
    assert settings.log_level == "INFO"
    assert settings.auth_token == ""
    assert settings.safe_execution_mode is True


def test_prefixed_env_names_still_work(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BLENDER_MCP_PORT", "2222")
    monkeypatch.setenv("BLENDER_MCP_SAFE_EXECUTION", "false")
    monkeypatch.setenv("BLENDER_MCP_SKETCHFAB_API_KEY", "key")
    settings = load_settings(tmp_path / "missing.toml")
    assert settings.port == 2222
    assert settings.safe_execution_mode is False
    assert settings.sketchfab_api_key == "key"


def test_toml_sets_safe_execution_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / "config.toml"
    cfg.write_text("[security]\nsafe_execution_mode = false\n", encoding="utf-8")
    assert load_settings(cfg).safe_execution_mode is False
