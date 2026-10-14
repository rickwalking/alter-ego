"""PT rendered slide JPEGs on disk. Never a public URL."""

from __future__ import annotations

from pathlib import Path

from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_PT,
    SLIDE_FILENAME_PREFIX,
    SLIDE_IMAGE_EXTENSION,
)
from rag_backend.modules.autopilot.constants import MAX_SLIDES


def pt_slide_paths(output_dir: str | None) -> tuple[str, ...]:
    """Up to 10 ``pt/slide_N.jpg`` paths, standard directory first, then HD."""
    if not output_dir:
        return ()
    root = Path(output_dir) / LANGUAGE_PT
    found = _numbered(root)
    if not found:
        found = _numbered(root / HD_SUBDIR_NAME)
    ordered = tuple(path for _number, path in sorted(found))
    return ordered[:MAX_SLIDES]


def _numbered(directory: Path) -> tuple[tuple[int, str], ...]:
    if not directory.is_dir():
        return ()
    pairs: list[tuple[int, str]] = []
    for path in directory.iterdir():
        number = _slide_number(path.name)
        if number is not None and path.is_file():
            pairs.append((number, str(path)))
    return tuple(pairs)


def _slide_number(name: str) -> int | None:
    prefix = SLIDE_FILENAME_PREFIX
    suffix = SLIDE_IMAGE_EXTENSION
    if not name.startswith(prefix) or not name.endswith(suffix):
        return None
    raw = name[len(prefix) : -len(suffix)]
    if not raw.isdigit():
        return None
    return int(raw)
