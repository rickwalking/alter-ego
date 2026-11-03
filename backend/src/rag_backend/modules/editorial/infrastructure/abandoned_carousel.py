"""Settle the carousel of an abandoned autopilot escalation.

When the autopilot closes an escalated run nobody fixed in time, the carousel
it escalated on still waits for a human. ``settle_abandoned_carousel`` moves it
to the terminal rejected state through the stuck-workflow auto-reject's own
transition (``WorkflowTimeoutRepository.reject``), with the same phase-changed
event, so the run and the carousel agree.

Only a carousel still waiting for a human, unchanged since the escalation, is
settled: the row is read under ``SELECT ... FOR UPDATE`` and must be awaiting a
human, not archived, not published, not approved for publish, not public, and
at the lock version the run escalated at. Anything else (already rejected,
approved, published, or edited since) is left alone, so a second call does
nothing. The write runs in a savepoint: a failure rolls back only the settle,
never the caller's transaction.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_STATUS_AWAITING_HUMAN,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.workflow_timeout import (
    ESCALATION_EXPIRED_EVENT_SOURCE,
    ESCALATION_EXPIRED_REJECT_MESSAGE,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.workflow_timeout_repository import (
    RejectCause,
    WorkflowTimeoutRepository,
)
from rag_backend.modules.editorial.infrastructure.cover_review_rollback import (
    row_for_update,
)


@dataclass(frozen=True, kw_only=True)
class AbandonedCarouselSettle:
    """The carousel, the lock version it escalated at, and the expiry window."""

    project_id: str
    expected_version: int
    idle_hours: int


async def settle_abandoned_carousel(
    session: AsyncSession,
    events: WorkflowEventService,
    command: AbandonedCarouselSettle,
) -> bool:
    """Reject the carousel if it still waits unchanged; True when it moved.

    The caller commits. Errors propagate after the savepoint rolled back.
    """
    async with session.begin_nested():
        project = await row_for_update(session, command.project_id)
        if project is None or not _waiting_unchanged(project, command):
            return False
        cause = RejectCause(
            reason=ESCALATION_EXPIRED_REJECT_MESSAGE,
            source=ESCALATION_EXPIRED_EVENT_SOURCE,
            timeout_hours=command.idle_hours,
        )
        await WorkflowTimeoutRepository(events).reject(session, project, cause)
    return True


def _waiting_unchanged(
    project: CarouselProjectModel, command: AbandonedCarouselSettle
) -> bool:
    """Waiting for a human, unreleased, at the version the run escalated at."""
    if project.phase_status != PHASE_STATUS_AWAITING_HUMAN:
        return False
    if project.archived_at is not None or project.current_phase == PHASE_PUBLISHED:
        return False
    if project.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH:
        return False
    if project.is_public:
        return False
    return int(project.lock_version or 1) == command.expected_version


__all__ = ["AbandonedCarouselSettle", "settle_abandoned_carousel"]
