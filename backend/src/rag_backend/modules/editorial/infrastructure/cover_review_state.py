"""``ReviewStateSource``: a carousel's approval and release, read fresh.

The two columns are selected directly (never through the session's identity
map), so a check under the project lock sees what is committed now, not the
row the request loaded earlier. ``lock_carousel_row`` holds the row for a
publisher's transaction, so it reads the approval and releases the carousel
before any slide-1 switch (which writes the row under its compare-and-set)
can land, or after it.
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


async def lock_carousel_row(session: AsyncSession, project_id: str) -> bool:
    """``SELECT ... FOR UPDATE`` (refreshed) until the caller commits; False
    when the carousel is gone."""
    from rag_backend.modules.editorial.infrastructure.cover_review_rollback import (
        row_for_update,
    )

    return await row_for_update(session, project_id) is not None


__all__ = ["EditorialReviewState", "lock_carousel_row"]
