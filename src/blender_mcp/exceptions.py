"""Typed exceptions and error codes for Blender MCP."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    BLENDER_NOT_CONNECTED = "BLENDER_NOT_CONNECTED"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    OPERATION_FAILED = "OPERATION_FAILED"
    SCRIPT_EXECUTION_FAILED = "SCRIPT_EXECUTION_FAILED"
    TIMEOUT = "TIMEOUT"
    ASSET_DOWNLOAD_FAILED = "ASSET_DOWNLOAD_FAILED"
    RENDER_FAILED = "RENDER_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    AUTH_FAILED = "AUTH_FAILED"
    PATH_DENIED = "PATH_DENIED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    RATE_LIMITED = "RATE_LIMITED"
    CONNECTION_ERROR = "CONNECTION_ERROR"


class BlenderMCPError(Exception):
    """Base error for Blender MCP operations."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.OPERATION_FAILED,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": False,
            "error_code": str(self.code),
            "error": self.message,
            "details": self.details,
        }


class BlenderNotConnectedError(BlenderMCPError):
    def __init__(self, message: str = "Blender is not connected", **kwargs: Any) -> None:
        super().__init__(message, code=ErrorCode.BLENDER_NOT_CONNECTED, **kwargs)


class ObjectNotFoundError(BlenderMCPError):
    def __init__(self, name: str, **kwargs: Any) -> None:
        super().__init__(
            f"Object not found: {name}",
            code=ErrorCode.OBJECT_NOT_FOUND,
            details={"object": name, **(kwargs.pop("details", {}) or {})},
            **kwargs,
        )


class InvalidParameterError(BlenderMCPError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, code=ErrorCode.INVALID_PARAMETER, **kwargs)


class TimeoutError_(BlenderMCPError):
    def __init__(self, message: str = "Operation timed out", **kwargs: Any) -> None:
        super().__init__(message, code=ErrorCode.TIMEOUT, **kwargs)


class PermissionDeniedError(BlenderMCPError):
    def __init__(self, message: str = "Permission denied", **kwargs: Any) -> None:
        super().__init__(message, code=ErrorCode.PERMISSION_DENIED, **kwargs)


class PathDeniedError(BlenderMCPError):
    def __init__(self, path: str, **kwargs: Any) -> None:
        super().__init__(
            f"Path access denied: {path}",
            code=ErrorCode.PATH_DENIED,
            details={"path": path},
            **kwargs,
        )


class AuthFailedError(BlenderMCPError):
    def __init__(self, message: str = "Bridge authentication failed", **kwargs: Any) -> None:
        super().__init__(message, code=ErrorCode.AUTH_FAILED, **kwargs)


class AssetDownloadFailedError(BlenderMCPError):
    def __init__(self, message: str = "Asset download failed", **kwargs: Any) -> None:
        super().__init__(message, code=ErrorCode.ASSET_DOWNLOAD_FAILED, **kwargs)
