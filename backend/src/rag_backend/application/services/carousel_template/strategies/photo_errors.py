"""Slide-1 photo errors shared by the hook-face and cover layouts.

PR #106 review: a POV slide 1 never renders without its photo. AE-0418: a
chosen GrokBot cover whose staged file is gone fails the same way
(``slide_cover_unreadable``) instead of rendering an empty slide 1.
"""

from __future__ import annotations

import os
from pathlib import Path

from rag_backend.domain.constants.slide_cover import (
    COVER_KIND_AI_IMAGE,
    ERR_SLIDE_COVER_UNREADABLE,
)
from rag_backend.domain.models import CarouselProject


class HookPhotoError(RuntimeError):
    """Slide 1 of a POV deck cannot render: its photo is missing or unreadable."""

    def __init__(self, code: str, project_id: str) -> None:
        super().__init__(f"{code}: project {project_id}")
        self.code = code
        self.project_id = project_id


def readable(path: Path) -> bool:
    """True when ``path`` is a file this process may read."""
    return path.is_file() and os.access(path, os.R_OK)


def slide_cover_src(project: CarouselProject) -> str | None:
    """The staged GrokBot cover, or None when the owner kept the default.

    Raises ``HookPhotoError(slide_cover_unreadable)`` when the output dir is
    known and the staged file is not readable there.
    """
    cover = project.slide_cover
    if cover is None:
        return None
    staged = Path(project.output_dir or "") / cover.staged_path
    if project.output_dir and not readable(staged):
        raise HookPhotoError(ERR_SLIDE_COVER_UNREADABLE, str(project.id))
    return cover.staged_path


def ai_cover_src(project: CarouselProject) -> str | None:
    """The cover to show full-bleed (an ``ai_image``), else None."""
    cover = project.slide_cover
    if cover is None or cover.kind != COVER_KIND_AI_IMAGE:
        return None
    return slide_cover_src(project)


__all__ = ["HookPhotoError", "ai_cover_src", "readable", "slide_cover_src"]
