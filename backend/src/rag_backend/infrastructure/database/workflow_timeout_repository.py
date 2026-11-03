"""Stuck-workflow auto-reject repository.

Implements :class:`StuckWorkflowAutoRejector`. CLAUDE.md mandates
"Auto-reject after timeout; never leave workflows stuck." The
``WorkflowFailureAlertService`` only *warns*; this repository performs the
actual terminal transition so a workflow is never left pending forever.

It lives in infrastructure (owns the ORM query + transition) so the worker /
application layer gains no new infrastructure import.

Only non-terminal phase statuses are eligible for auto-reject: ``in_progress``
is excluded (a workflow may be running or resuming) and terminal states
(approved, rejected, failed) are excluded by construction.

``reject`` is the one terminal transition: the stuck sweep calls it with the
stuck cause, and the editorial settle of an abandoned autopilot escalation
calls it with its own cause, so both write the same row state and the same
phase-changed event.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_PENDING,
    PHASE_STATUS_REJECTED,
)
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_PROJECT,
    EVENT_TYPE_PROJECT_PHASE_CHANGED,
)
from rag_backend.domain.constants.workflow_timeout import (
    AUTO_REJECT_CAROUSEL_STATUS,
    AUTO_REJECT_ERROR_MESSAGE,
    AUTO_REJECT_EVENT_SOURCE,
    AUTO_REJECT_LOG_EVENT,
    AUTO_REJECT_PAYLOAD_NEW_PHASE_STATUS,
    AUTO_REJECT_PAYLOAD_PREVIOUS_PHASE,
    AUTO_REJECT_PAYLOAD_PREVIOUS_PHASE_STATUS,
    AUTO_REJECT_PAYLOAD_REASON,
    AUTO_REJECT_PAYLOAD_TIMEOUT_HOURS,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_AUTO_REJECT_ELIGIBLE_PHASE_STATUSES: frozenset[str] = frozenset({
    PHASE_STATUS_PENDING,
    PHASE_STATUS_AWAITING_HUMAN,
})

_EVENT_SOURCE_KEY = "source"


@dataclass(frozen=True, kw_only=True)
class RejectCause:
    """Why a carousel is rejected: the stored message, event source and window."""

    reason: str
    source: str
    timeout_hours: int

    @classmethod
    def stuck(cls, timeout_hours: int) -> RejectCause:
        """The stuck-workflow timeout cause."""
        return cls(
            reason=AUTO_REJECT_ERROR_MESSAGE,
            source=AUTO_REJECT_EVENT_SOURCE,
            timeout_hours=timeout_hours,
        )


class WorkflowTimeoutRepository:
    """ORM-backed auto-reject of timed-out carousel workflows."""

    def __init__(self, event_service: WorkflowEventService) -> None:
        self._events = event_service

    async def auto_reject_stuck(self, db: AsyncSession, timeout_hours: int) -> int:
        """Auto-reject every workflow past ``timeout_hours``; return the count.

        A workflow is stuck when it is not yet published, sits in a non-terminal
        pending-like phase status, and has not been updated within the timeout
        window. Each match is transitioned to ``rejected`` (terminal) and emits
        the existing phase-changed event.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=timeout_hours)
        stuck = await self._find_stuck(db, cutoff)
        cause = RejectCause.stuck(timeout_hours)
        for project in stuck:
            await self.reject(db, project, cause)
        return len(stuck)

    @staticmethod
    async def _find_stuck(
        db: AsyncSession, cutoff: datetime
    ) -> list[CarouselProjectModel]:
        result = await db.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.current_phase != PHASE_PUBLISHED,
                CarouselProjectModel.phase_status.in_(
                    _AUTO_REJECT_ELIGIBLE_PHASE_STATUSES
                ),
                CarouselProjectModel.archived_at.is_(None),
                CarouselProjectModel.updated_at <= cutoff,
            )
        )
        return list(result.scalars().all())

    async def reject(
        self,
        db: AsyncSession,
        project: CarouselProjectModel,
        cause: RejectCause,
    ) -> None:
        """Move ``project`` to the terminal rejected state and emit the event.

        The caller chose the row and commits. The phase-changed payload carries
        the previous phase and status, the reason and the time window.
        """
        project_id = str(project.id)
        previous_phase = project.current_phase
        previous_phase_status = project.phase_status
        project.phase_status = PHASE_STATUS_REJECTED
        project.status = AUTO_REJECT_CAROUSEL_STATUS
        project.error_message = cause.reason
        logger.warning(
            AUTO_REJECT_LOG_EVENT,
            project_id=project_id,
            previous_phase=previous_phase,
            previous_phase_status=previous_phase_status,
            timeout_hours=cause.timeout_hours,
            source=cause.source,
        )
        await self._events.emit(
            db,
            event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
            aggregate_id=project_id,
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            payload={
                AUTO_REJECT_PAYLOAD_PREVIOUS_PHASE: previous_phase,
                AUTO_REJECT_PAYLOAD_PREVIOUS_PHASE_STATUS: previous_phase_status,
                AUTO_REJECT_PAYLOAD_NEW_PHASE_STATUS: PHASE_STATUS_REJECTED,
                AUTO_REJECT_PAYLOAD_REASON: cause.reason,
                AUTO_REJECT_PAYLOAD_TIMEOUT_HOURS: cause.timeout_hours,
            },
            metadata={_EVENT_SOURCE_KEY: cause.source},
        )


__all__ = ["RejectCause", "WorkflowTimeoutRepository"]
