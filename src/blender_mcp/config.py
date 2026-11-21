"""Configuration loading for Blender MCP."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScriptPermission(StrEnum):
    RESTRICTED = "restricted"
    CONFIRMATION = "confirmation"
    TRUSTED = "trusted"


class BridgeConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 9877
    auth_token: str = ""
    connection_timeout: float = 5.0
    request_timeout: float = 60.0
    # Per-command timeouts in seconds, e.g. {"render_animation": 3600}. Overrides the
    # built-in slow-command defaults in blender_mcp.protocol.timeouts.
    command_timeouts: dict[str, float] = Field(default_factory=dict)
    # Extra seconds to wait past a command's timeout for the addon's own timeout reply.
    response_grace: float = 10.0
    retry_count: int = 3
    retry_delay: float = 0.5
    heartbeat_interval: float = 15.0
    allow_remote: bool = False


class SecurityConfig(BaseModel):
    safe_execution_mode: bool = True
    script_permission: ScriptPermission = ScriptPermission.TRUSTED
    confirm_destructive: bool = True
    confirm_overwrite: bool = True
    max_request_bytes: int = 1_048_576
    allowed_directories: list[str] = Field(default_factory=list)


class ScreenshotConfig(BaseModel):
    default_max_size: int = 1024
    format: str = "png"
    include_ui: bool = False


class RenderConfig(BaseModel):
    max_samples: int = 128
    max_resolution_x: int = 1920
    max_resolution_y: int = 1080
    max_time_seconds: int = 300
    default_engine: str = "CYCLES"


class ToolGroupsConfig(BaseModel):
    scene: bool = True
    objects: bool = True
    meshes: bool = True
    modifiers: bool = True
    materials: bool = True
    geometry_nodes: bool = True
    cameras: bool = True
    lighting: bool = True
    rendering: bool = True
    animation: bool = True
    assets: bool = True
    import_export: bool = True
    collections: bool = True
    screenshots: bool = True
    scripting: bool = True


class ProvidersConfig(BaseModel):
    polyhaven: bool = True
    sketchfab: bool = False
    polypizza: bool = False
    meshy: bool = False
    tripo: bool = False
    rodin: bool = False
    hunyuan3d: bool = False
    sketchfab_api_key: str = ""
    polypizza_api_key: str = ""
    meshy_api_key: str = ""
    tripo_api_key: str = ""
    rodin_api_key: str = ""
    hunyuan_secret_id: str = ""
    hunyuan_secret_key: str = ""


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = ""


class Settings(BaseSettings):
    """Runtime settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_prefix="BLENDER_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=9877, alias="PORT")
    auth_token: str = Field(default="", alias="AUTH_TOKEN")
    connection_timeout: float = Field(default=5.0, alias="CONNECTION_TIMEOUT")
    request_timeout: float = Field(default=60.0, alias="REQUEST_TIMEOUT")
    command_timeouts: dict[str, float] = Field(default_factory=dict)
    retry_count: int = Field(default=3, alias="RETRY_COUNT")
    retry_delay: float = Field(default=0.5, alias="RETRY_DELAY")
    heartbeat_interval: float = Field(default=15.0, alias="HEARTBEAT_INTERVAL")
    allow_remote: bool = Field(default=False, alias="ALLOW_REMOTE")

    safe_execution_mode: bool = Field(default=True, alias="SAFE_EXECUTION")
    script_permission: ScriptPermission = Field(
        default=ScriptPermission.TRUSTED, alias="SCRIPT_PERMISSION"
    )
    confirm_destructive: bool = True
    confirm_overwrite: bool = True
    max_request_bytes: int = 1_048_576
    allowed_directories: list[str] = Field(default_factory=list)

    screenshot_max_size: int = 1024
    screenshot_format: str = "png"

    render_max_samples: int = 128
    render_max_resolution_x: int = 1920
    render_max_resolution_y: int = 1080
    render_max_time_seconds: int = 300
    render_default_engine: str = "CYCLES"

    # Path to the Blender executable for open_blender; empty means auto-detect.
    blender_path: str = Field(default="", alias="BLENDER_PATH")
    blender_launch_timeout: float = Field(default=60.0, alias="BLENDER_LAUNCH_TIMEOUT")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = ""

    polyhaven: bool = True
    sketchfab: bool = False
    polypizza: bool = False
    meshy: bool = False
    tripo: bool = False
    rodin: bool = False
    hunyuan3d: bool = False

    sketchfab_api_key: str = Field(default="", alias="SKETCHFAB_API_KEY")
    polypizza_api_key: str = Field(default="", alias="POLYPIZZA_API_KEY")
    meshy_api_key: str = Field(default="", alias="MESHY_API_KEY")
    tripo_api_key: str = Field(default="", alias="TRIPO_API_KEY")
    rodin_api_key: str = Field(default="", alias="RODIN_API_KEY")
    hunyuan_secret_id: str = Field(default="", alias="HUNYUAN_SECRET_ID")
    hunyuan_secret_key: str = Field(default="", alias="HUNYUAN_SECRET_KEY")

    tool_groups: ToolGroupsConfig = Field(default_factory=ToolGroupsConfig)
    # "core": a small, high-leverage tool set (default; best for LLM accuracy).
    # "full": every specialised tool (~170) for clients that want narrow wrappers.
    tool_profile: str = Field(default="core", alias="TOOL_PROFILE")

    @field_validator("tool_profile", mode="before")
    @classmethod
    def _check_profile(cls, value: Any) -> str:
        value = (value or "core").strip().lower()
        if value not in ("core", "full"):
            raise ValueError("tool_profile must be 'core' or 'full'")
        return value

    @field_validator("allowed_directories", mode="before")
    @classmethod
    def _split_dirs(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(os.pathsep) if part.strip()]
        return list(value)

    def bridge(self) -> BridgeConfig:
        return BridgeConfig(
            host=self.host,
            port=self.port,
            auth_token=self.auth_token,
            connection_timeout=self.connection_timeout,
            request_timeout=self.request_timeout,
            command_timeouts=dict(self.command_timeouts),
            retry_count=self.retry_count,
            retry_delay=self.retry_delay,
            heartbeat_interval=self.heartbeat_interval,
            allow_remote=self.allow_remote,
        )

    def security(self) -> SecurityConfig:
        return SecurityConfig(
            safe_execution_mode=self.safe_execution_mode,
            script_permission=self.script_permission,
            confirm_destructive=self.confirm_destructive,
            confirm_overwrite=self.confirm_overwrite,
            max_request_bytes=self.max_request_bytes,
            allowed_directories=self.allowed_directories,
        )

    def screenshots(self) -> ScreenshotConfig:
        return ScreenshotConfig(
            default_max_size=self.screenshot_max_size,
            format=self.screenshot_format,
        )

    def render(self) -> RenderConfig:
        return RenderConfig(
            max_samples=self.render_max_samples,
            max_resolution_x=self.render_max_resolution_x,
            max_resolution_y=self.render_max_resolution_y,
            max_time_seconds=self.render_max_time_seconds,
            default_engine=self.render_default_engine,
        )

    def providers(self) -> ProvidersConfig:
        return ProvidersConfig(
            polyhaven=self.polyhaven,
            sketchfab=self.sketchfab,
            polypizza=self.polypizza,
            meshy=self.meshy,
            tripo=self.tripo,
            rodin=self.rodin,
            hunyuan3d=self.hunyuan3d,
            sketchfab_api_key=self.sketchfab_api_key,
            polypizza_api_key=self.polypizza_api_key,
            meshy_api_key=self.meshy_api_key,
            tripo_api_key=self.tripo_api_key,
            rodin_api_key=self.rodin_api_key,
            hunyuan_secret_id=self.hunyuan_secret_id,
            hunyuan_secret_key=self.hunyuan_secret_key,
        )


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore

    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings from optional TOML file, then apply environment overrides."""
    overrides: dict[str, Any] = {}
    path = Path(config_path) if config_path else Path("config.toml")
    if path.is_file():
        raw = _load_toml(path)
        bridge = raw.get("bridge", {})
        security = raw.get("security", {})
        screenshots = raw.get("screenshots", {})
        render = raw.get("render", {})
        logging_cfg = raw.get("logging", {})
        providers = raw.get("providers", {})
        tool_groups = raw.get("tool_groups", {})
        tools_cfg = raw.get("tools", {})

        overrides.update(
            {
                "host": bridge.get("host", "127.0.0.1"),
                "port": bridge.get("port", 9877),
                "auth_token": bridge.get("auth_token", ""),
                "connection_timeout": bridge.get("connection_timeout", 5.0),
                "request_timeout": bridge.get("request_timeout", 60.0),
                "command_timeouts": bridge.get("command_timeouts", {}),
                "retry_count": bridge.get("retry_count", 3),
                "retry_delay": bridge.get("retry_delay", 0.5),
                "heartbeat_interval": bridge.get("heartbeat_interval", 15.0),
                "allow_remote": bridge.get("allow_remote", False),
                "safe_execution_mode": security.get("safe_execution_mode", True),
                "script_permission": security.get("script_permission", "restricted"),
                "confirm_destructive": security.get("confirm_destructive", True),
                "confirm_overwrite": security.get("confirm_overwrite", True),
                "max_request_bytes": security.get("max_request_bytes", 1_048_576),
                "allowed_directories": security.get("allowed_directories", []),
                "screenshot_max_size": screenshots.get("default_max_size", 1024),
                "screenshot_format": screenshots.get("format", "png"),
                "render_max_samples": render.get("max_samples", 128),
                "render_max_resolution_x": render.get("max_resolution_x", 1920),
                "render_max_resolution_y": render.get("max_resolution_y", 1080),
                "render_max_time_seconds": render.get("max_time_seconds", 300),
                "render_default_engine": render.get("default_engine", "CYCLES"),
                "log_level": logging_cfg.get("level", "INFO"),
                "log_file": logging_cfg.get("file", ""),
                "polyhaven": providers.get("polyhaven", True),
                "sketchfab": providers.get("sketchfab", False),
                "polypizza": providers.get("polypizza", False),
                "meshy": providers.get("meshy", False),
                "tripo": providers.get("tripo", False),
                "rodin": providers.get("rodin", False),
                "hunyuan3d": providers.get("hunyuan3d", False),
                "tool_groups": ToolGroupsConfig(**tool_groups)
                if tool_groups
                else ToolGroupsConfig(),
            }
        )

        if "profile" in tools_cfg:
            overrides["tool_profile"] = tools_cfg["profile"]

        blender_cfg = raw.get("blender", {})
        if "path" in blender_cfg:
            overrides["blender_path"] = blender_cfg["path"]
        if "launch_timeout" in blender_cfg:
            overrides["blender_launch_timeout"] = blender_cfg["launch_timeout"]

    return Settings(**overrides)
