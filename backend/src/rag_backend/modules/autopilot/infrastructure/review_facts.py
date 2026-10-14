"""Title, caption, PT slide paths, and the profile line for a review message."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.notify import ReviewFacts
from rag_backend.modules.autopilot.infrastructure.slide_files import pt_slide_paths
from rag_backend.modules.editorial.public import CarouselAutomationAcl


class CarouselReviewFacts:
    """Reads the private carousel through the editorial facade. Publishes nothing."""

    def __init__(self, session: AsyncSession) -> None:
        self._acl = CarouselAutomationAcl(session)

    async def load(self, project_id: str) -> ReviewFacts | None:
        """Return facts, or None when the carousel does not exist."""
        row = await self._acl.review_row(project_id)
        if row is None:
            return None
        return ReviewFacts(
            title=row.topic,
            caption=row.caption,
            slide_paths=pt_slide_paths(row.output_dir),
            audience=row.audience,
            niche=row.niche,
            image_style=row.image_style,
        )
