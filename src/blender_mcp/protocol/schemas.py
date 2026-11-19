"""Pydantic schemas for bridge protocol validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuthMessage(BaseModel):
    type: str = "auth"
    token: str = ""


class PingMessage(BaseModel):
    type: str = "ping"
    id: str = ""


class PongMessage(BaseModel):
    type: str = "pong"
    id: str = ""


class RequestMessage(BaseModel):
    type: str = "request"
    id: str
    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class ResponseMessage(BaseModel):
    type: str = "response"
    id: str
    success: bool
    result: Any = None
    error_code: str | None = None
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float | None = None


class StatusMessage(BaseModel):
    type: str = "status"
    connected: bool
    blender_version: str | None = None
    addon_version: str | None = None
    client_count: int = 0
