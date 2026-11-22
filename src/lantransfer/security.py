from __future__ import annotations

import re
import secrets
from pathlib import Path

_UNSAFE_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def generate_token(nbytes: int = 16) -> str:
    """Generate a cryptographically secure URL-safe session token."""
    return secrets.token_urlsafe(nbytes)


def verify_token(expected: str, provided: str | None) -> bool:
    """Verify a session token using constant-time comparison."""
    if not expected or not provided:
        return False
    return secrets.compare_digest(expected, provided)


def sanitize_filename(raw_name: str) -> str:
    """Strip directory components and unsafe characters from an uploaded filename."""
    normalized = raw_name.replace("\\", "/")
    base = normalized.rsplit("/", 1)[-1].strip()
    cleaned = _UNSAFE_CHARS_RE.sub("_", base).strip(". ")
    return cleaned or "unnamed_file"


def resolve_unique_path(directory: Path, raw_filename: str) -> Path:
    """
    Return a safe, non-colliding file path strictly inside `directory`.
    Appends ' (1)', ' (2)', etc. if a file with the same name already exists.
    """
    base_dir = directory.resolve()
    safe_name = sanitize_filename(raw_filename)
    candidate = (base_dir / safe_name).resolve()

    if base_dir not in candidate.parents:
        raise ValueError(f"Resolved path escapes target directory: {raw_filename}")

    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        numbered = base_dir / f"{stem} ({counter}){suffix}"
        if not numbered.exists():
            return numbered
        counter += 1
