"""Bridge message types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


def new_request_id() -> str:
    return uuid4().hex


@dataclass
class BridgeRequest:
    command: str
    params: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=new_request_id)
    # Seconds the addon may spend on this request (queued + running). None: addon default.
    timeout: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "request",
            "id": self.id,
            "command": self.command,
            "params": self.params,
        }
        if self.timeout is not None:
            payload["timeout"] = self.timeout
        return payload


@dataclass
class BridgeResponse:
    id: str
    success: bool
    result: Any = None
    error_code: str | None = None
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BridgeResponse:
        return cls(
            id=str(data.get("id", "")),
            success=bool(data.get("success", False)),
            result=data.get("result"),
            error_code=data.get("error_code"),
            error=data.get("error") or data.get("message"),
            details=data.get("details") or {},
            duration_ms=data.get("duration_ms"),
        )

    def to_tool_result(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "success": self.success,
            "result": self.result,
            "operation_id": self.id,
        }
        if self.duration_ms is not None:
            payload["duration_ms"] = self.duration_ms
        if not self.success:
            payload["error_code"] = self.error_code or "OPERATION_FAILED"
            payload["error"] = self.error or "Unknown error"
            if self.details:
                payload["details"] = self.details
        return payload
