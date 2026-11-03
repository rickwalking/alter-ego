"""``CarouselSettler`` over the editorial facade's abandoned-carousel settle.

The editorial module owns the carousel row and the reject transition; this
adapter only maps the autopilot command and supplies the session and the
workflow event service the phase-changed event is written through.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.modules.autopilot.domain.recovery import CarouselSettle
from rag_backend.modules.editorial.public import (
    AbandonedCarouselSettle,
    settle_abandoned_carousel,
)


class EditorialCarouselSettler:
    """Session-scoped. The worker tick commits."""

    def __init__(self, session: AsyncSession, events: WorkflowEventService) -> None:
        self._session = session
        self._events = events

    async def settle_abandoned(self, settle: CarouselSettle) -> bool:
        """Reject the carousel if it still waits unchanged; True when it moved."""
        return await settle_abandoned_carousel(
            self._session,
            self._events,
            AbandonedCarouselSettle(
                project_id=settle.project_id,
                expected_version=settle.expected_version,
                idle_hours=settle.idle_hours,
            ),
        )


def carousel_settler(session: AsyncSession) -> EditorialCarouselSettler:
    """The settler on ``session`` with the process event publisher."""
    publisher = get_event_publisher(get_settings().redis_url or None)
    return EditorialCarouselSettler(session, WorkflowEventService(publisher))


__all__ = ["EditorialCarouselSettler", "carousel_settler"]
