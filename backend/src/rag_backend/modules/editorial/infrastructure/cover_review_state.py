"""``ReviewStateSource``: a carousel's approval and release, read fresh.

The two columns are selected directly (never through the session's identity
map), so a check under the project lock sees what is committed now, not the
row the request loaded earlier.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_switch_guard import ReviewState


class EditorialReviewState:
    """The committed ``workflow_status`` and ``is_public`` of one carousel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def review_state(self, project_id: str) -> ReviewState | None:
        """The committed state; None for an unknown carousel."""
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel as Row,
        )

        found = (
            await self._session.execute(
                select(Row.workflow_status, Row.is_public).where(Row.id == project_id)
            )
        ).one_or_none()
        if found is None:
            return None
        return ReviewState(
            workflow_status=str(found.workflow_status or ""),
            is_public=bool(found.is_public),
        )


__all__ = ["EditorialReviewState"]
