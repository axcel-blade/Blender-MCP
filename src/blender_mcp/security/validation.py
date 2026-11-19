"""Path and parameter validation."""

from __future__ import annotations

from pathlib import Path

from blender_mcp.exceptions import InvalidParameterError, PathDeniedError


def validate_path(
    path: str,
    *,
    allowed_directories: list[str] | None = None,
    must_exist: bool = False,
    allow_create: bool = True,
) -> Path:
    """Resolve a path and optionally enforce allow-list / existence rules."""
    if not path or not str(path).strip():
        raise InvalidParameterError("Path must be a non-empty string")

    resolved = Path(path).expanduser().resolve()

    if allowed_directories:
        allowed = [Path(d).expanduser().resolve() for d in allowed_directories if d]
        if allowed and not any(_is_relative_to(resolved, root) for root in allowed):
            raise PathDeniedError(str(resolved))

    if must_exist and not resolved.exists():
        raise InvalidParameterError(f"Path does not exist: {resolved}")

    if not allow_create and not resolved.exists():
        raise InvalidParameterError(f"Path does not exist: {resolved}")

    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def require_non_empty(name: str, value: str | None) -> str:
    if value is None or not str(value).strip():
        raise InvalidParameterError(f"Parameter '{name}' is required")
    return str(value).strip()
