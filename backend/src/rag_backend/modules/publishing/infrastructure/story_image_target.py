"""Render the carousel's Story image before Meta fetches it."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.publishing.application.story_image import (
    StoryPaths,
    render_story_image,
    story_paths,
)
from rag_backend.modules.publishing.domain.instagram_target import StoryImageTarget

logger = get_logger()


async def prepare_story_image(
    session: AsyncSession,
    project_id: str,
) -> StoryImageTarget | None:
    """Render ``story_pt.jpg`` when needed. None when the carousel does not exist."""
    project = await session.get(CarouselProjectModel, project_id)
    if project is None:
        return None
    paths = story_paths(_text(project.output_dir), _text(project.artifact_version))
    ready = await asyncio.to_thread(_render, paths)
    return StoryImageTarget(
        ready=ready,
        niche=_text(project.niche) or "",
        image_style=_text(project.image_style) or "",
    )


def _render(paths: StoryPaths | None) -> bool:
    """Pillow's ``UnidentifiedImageError`` is an ``OSError``; the Story is optional."""
    if paths is None:
        return False
    try:
        return render_story_image(paths)
    except (OSError, ValueError) as exc:
        logger.warning("story_image_render_failed", error=type(exc).__name__)
        return False


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None
