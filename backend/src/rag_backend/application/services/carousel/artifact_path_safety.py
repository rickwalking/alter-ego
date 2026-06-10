"""Path-safety helpers for carousel artifact file resolution."""

from __future__ import annotations

import re
from pathlib import Path

_SAFE_SLIDE_IMAGE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def sanitize_slide_image_filename(filename: str) -> str | None:
    """Return a safe basename or None when the filename is unsafe."""
    if ".." in filename or "/" in filename or "\\" in filename:
        return None
    basename = Path(filename).name
    if not basename or basename in {".", ".."}:
        return None
    if not _SAFE_SLIDE_IMAGE_FILENAME.match(basename):
        return None
    return basename


def resolve_confined_slide_image(base_dir: Path, filename: str) -> Path | None:
    """Resolve a slide image path confined to base_dir."""
    safe_name = sanitize_slide_image_filename(filename)
    if safe_name is None:
        return None
    resolved_base = base_dir.resolve()
    candidate = (resolved_base / safe_name).resolve()
    if not candidate.is_relative_to(resolved_base):
        return None
    if candidate.is_file():
        return candidate
    with_ext = candidate.with_suffix(".jpg")
    if with_ext.is_file() and with_ext.is_relative_to(resolved_base):
        return with_ext
    return None


__all__ = ["resolve_confined_slide_image", "sanitize_slide_image_filename"]
