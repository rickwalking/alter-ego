"""Title, caption, PT slide paths, and the profile line for a review message."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.autofix import (
    ContentAutofixer,
    QualityIssues,
)
from rag_backend.modules.autopilot.domain.notify import ReviewFacts
from rag_backend.modules.autopilot.infrastructure.slide_files import pt_slide_paths
from rag_backend.modules.autopilot.notify_constants import LOG_REVIEW_ISSUES_FAILED
from rag_backend.modules.editorial.public import CarouselAutomationAcl

logger = structlog.get_logger()


class CarouselReviewFacts:
    """Reads the private carousel through the editorial facade. Publishes nothing."""

    def __init__(
        self,
        session: AsyncSession,
        autofixer: ContentAutofixer | None = None,
    ) -> None:
        self._acl = CarouselAutomationAcl(session)
        self._autofixer = autofixer

    async def load(self, project_id: str) -> ReviewFacts | None:
        """Return facts, or None when the carousel does not exist."""
        row = await self._acl.review_row(project_id)
        if row is None:
            return None
        issues = await self._issues(project_id)
        return ReviewFacts(
            title=row.topic,
            caption=row.caption,
            slide_paths=pt_slide_paths(row.output_dir),
            audience=row.audience,
            niche=row.niche,
            image_style=row.image_style,
            issues=issues.lines,
            fixable=issues.fixable,
        )

    async def _issues(self, project_id: str) -> QualityIssues:
        """The quality issues the review lists, and the fix button.

        An inspection error is logged and the review still goes out without the
        list.
        """
        if self._autofixer is None:
            return QualityIssues()
        try:
            return await self._autofixer.inspect(project_id)
        except Exception as exc:
            logger.warning(
                LOG_REVIEW_ISSUES_FAILED,
                project_id=project_id,
                error=type(exc).__name__,
            )
            return QualityIssues()
