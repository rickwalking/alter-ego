"""Failure and stuck-resume persistence for editorial workflow resumes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel.workflow_failure_cause import (
    failure_cause,
    failure_cause_code,
)
from rag_backend.domain.constants.carousel_run import RUN_FINISHED_REASON_FAILED
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_STUCK,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
)
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner
from rag_backend.modules.generation_queue.events_public import (
    OUTCOME_FAILED,
    WorkflowOutcomeObservation,
    note_workflow_failure,
    record_workflow_outcome,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.editorial_workflow_service import (
        EditorialWorkflowService,
    )


@dataclass(frozen=True)
class MarkFailedParams:
    """Inputs for marking a background resume as failed.

    ``message`` is the client-safe SSE message; ``cause`` is the safe
    ``<ErrorClass>: <code>`` stored on the carousel row.
    """

    service: EditorialWorkflowService
    project_id: str
    message: str
    recoverable: bool
    cause: str


@dataclass(frozen=True)
class RevertContext:
    service: EditorialWorkflowService
    project_id: str
    prior_phase: str
    session_factory: async_sessionmaker[AsyncSession]
    publish: Callable[..., Awaitable[None]]


async def revert_background_resume_stuck(context: RevertContext) -> None:
    """Revert DB phase_status to awaiting_human and publish error SSE."""
    async with context.session_factory() as db:
        await CarouselProjectWriteOwner(db).set_phase_status_and_commit(
            context.project_id,
            PHASE_STATUS_AWAITING_HUMAN,
        )
        await context.service.publish_resume_error_event(
            context.project_id,
            message=ERR_BACKGROUND_RESUME_STUCK,
            recoverable=True,
        )
        await context.publish(
            context.project_id,
            RUN_FINISHED_REASON_FAILED,
            final_phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )


async def mark_background_resume_failed(
    params: MarkFailedParams,
    session_factory: async_sessionmaker[AsyncSession],
    publish: Callable[..., Awaitable[None]],
) -> None:
    async with session_factory() as db:
        await CarouselProjectWriteOwner(db).mark_phase_failed_and_commit(
            params.project_id, params.cause
        )
        await params.service.publish_resume_error_event(
            params.project_id,
            message=params.message,
            recoverable=params.recoverable,
        )
        await publish(
            params.project_id,
            RUN_FINISHED_REASON_FAILED,
            final_phase_status=PHASE_STATUS_FAILED,
        )


@dataclass(frozen=True)
class FailedResume:
    """Where a resume failed (the phase it resumed from) and the event's code."""

    project_id: str
    phase: str
    error_code: str


async def record_resume_failure(failed: FailedResume, exc: Exception) -> None:
    """The ``workflow_failed`` event with class and code; the run notes the cause."""
    await record_workflow_outcome(
        WorkflowOutcomeObservation(
            project_id=failed.project_id,
            phase=failed.phase,
            outcome=OUTCOME_FAILED,
            error_code=failed.error_code,
            error_type=type(exc).__name__,
            reason=failure_cause_code(exc),
        )
    )
    note_workflow_failure(failure_cause(exc))


__all__ = [
    "FailedResume",
    "MarkFailedParams",
    "RevertContext",
    "mark_background_resume_failed",
    "record_resume_failure",
    "revert_background_resume_stuck",
]
