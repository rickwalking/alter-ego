"""Shared image validation utilities for carousel pipeline."""

from __future__ import annotations

from pathlib import Path

_MIN_JPEG_BYTES = 1024


def is_valid_jpeg(path: Path, min_bytes: int = _MIN_JPEG_BYTES) -> bool:
    """Check whether a file is a valid JPEG with minimum size.

    Returns False for files that are too small, have wrong format,
    cannot be opened, or fail PIL verification.
    """
    try:
        if not path.is_file():
            return False
        if path.stat().st_size < min_bytes:
            return False
        from PIL import Image as PILImage

        with PILImage.open(path) as image:
            if image.format != "JPEG":
                return False
            image.verify()
    except (OSError, ValueError):
        return False
    else:
        return True
