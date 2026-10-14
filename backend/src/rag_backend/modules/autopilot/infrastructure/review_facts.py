"""Title, caption, and PT slide paths for a review message."""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.notify import ReviewFacts
from rag_backend.modules.autopilot.infrastructure.slide_files import pt_slide_paths


class CarouselReviewFacts:
    """Reads the private carousel row. Does not publish anything."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, project_id: str) -> ReviewFacts | None:
        """Return facts, or None when the carousel does not exist."""
        project = await self._session.get(CarouselProjectModel, project_id)
        if project is None:
            return None
        output_dir = cast(str | None, project.output_dir)
        return ReviewFacts(
            title=_text(project.topic),
            caption=_text(project.caption),
            slide_paths=pt_slide_paths(output_dir),
        )


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""
