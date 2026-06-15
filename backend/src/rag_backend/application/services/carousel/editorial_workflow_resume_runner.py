"""Background execution for async editorial workflow resume (RW-010-RW-013)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from rag_backend.application.services.carousel.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    ResumeWorkflowInput,
    publish_workflow_sse_updates,
    resolve_background_resume_sse_error_message,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_BACKGROUND_RESUME_STUCK,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    REVIEW_ACTION_APPROVE,
)
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_background_tasks: set[asyncio.Task[None]] = set()


@dataclass(frozen=True)
class _MarkFailedParams:
    """Inputs for marking a background resume as failed."""

    service: EditorialWorkflowService
    project_id: str
    message: str
    recoverable: bool


@dataclass(frozen=True)
class BackgroundResumeParams:
    """Inputs required to resume a workflow in the background."""

    project_id: str
    action: str
    reviewer_id: str
    feedback: str | None
    project_title: str
    structured_feedback: dict[str, object] | None


def schedule_background_resume(
    service: EditorialWorkflowService,
    params: BackgroundResumeParams,
) -> None:
    """Fire-and-forget background resume with task tracking."""
    task = asyncio.create_task(
        _execute_background_resume(service, params),
        name=f"workflow-resume-{params.project_id}",
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _execute_background_resume(
    service: EditorialWorkflowService,
    params: BackgroundResumeParams,
) -> None:
    session_factory = get_session_maker()
    async with session_factory() as db:
        try:
            prior_state = await service.get_workflow_state(params.project_id)
            prior_phase = (
                str(prior_state.get("current_phase", "")) if prior_state else ""
            )

            state = await service.resume_workflow(
                ResumeWorkflowInput(
                    project_id=params.project_id,
                    action=params.action,
                    reviewer_id=params.reviewer_id,
                    feedback=params.feedback,
                    db=db,
                    persona=None,
                    project_title=params.project_title,
                    structured_feedback=params.structured_feedback,
                ),
            )

            if _detect_resume_stuck(
                params,
                prior_phase,
                state,
            ):
                logger.warning(
                    "background_resume_stuck",
                    project_id=params.project_id,
                    phase=prior_phase,
                    action=params.action,
                )
                await _revert_background_resume_stuck(
                    service,
                    params.project_id,
                    prior_phase,
                )
                return

            await CarouselProjectWriteOwner(db).commit()
            await publish_workflow_sse_updates(params.project_id, state)
        except ValueError as exc:
            await db.rollback()
            detail = resolve_background_resume_sse_error_message(str(exc))
            if detail in {
                ERR_REVISION_CAP_EXCEEDED,
                ERR_PERSONA_SCORE_TOO_LOW,
            }:
                logger.warning(
                    "background_resume_validation_failed",
                    project_id=params.project_id,
                    detail=detail,
                )
            await _mark_background_resume_failed(
                _MarkFailedParams(
                    service=service,
                    project_id=params.project_id,
                    message=detail,
                    recoverable=detail != ERR_REVISION_CAP_EXCEEDED,
                ),
            )
        except Exception:
            await db.rollback()
            logger.exception(
                "background_resume_failed",
                project_id=params.project_id,
            )
            await _mark_background_resume_failed(
                _MarkFailedParams(
                    service=service,
                    project_id=params.project_id,
                    message=ERR_BACKGROUND_RESUME_FAILED,
                    recoverable=True,
                ),
            )


def _detect_resume_stuck(
    params: BackgroundResumeParams,
    prior_phase: str,
    state: dict[str, object],
) -> bool:
    """Return True when an approve resume completed but phase did not advance.

    Revise and reject actions legitimately return to the same phase with
    awaiting_human — stuck detection is scoped to approve only.
    """
    if params.action != REVIEW_ACTION_APPROVE:
        return False
    current_phase = str(state.get("current_phase", ""))
    current_status = str(state.get("phase_status", ""))
    return bool(
        prior_phase
        and current_phase == prior_phase
        and current_status == PHASE_STATUS_AWAITING_HUMAN
    )


async def _revert_background_resume_stuck(
    service: EditorialWorkflowService,
    project_id: str,
    _prior_phase: str,
) -> None:
    """Revert DB phase_status to awaiting_human and publish error SSE."""
    session_factory = get_session_maker()
    async with session_factory() as db:
        await CarouselProjectWriteOwner(db).set_phase_status_and_commit(
            project_id,
            PHASE_STATUS_AWAITING_HUMAN,
        )
        await service.publish_resume_error_event(
            project_id,
            message=ERR_BACKGROUND_RESUME_STUCK,
            recoverable=True,
        )


async def _mark_background_resume_failed(
    params: _MarkFailedParams,
) -> None:
    session_factory = get_session_maker()
    async with session_factory() as db:
        await CarouselProjectWriteOwner(db).set_phase_status_and_commit(
            params.project_id,
            PHASE_STATUS_FAILED,
        )
        await params.service.publish_resume_error_event(
            params.project_id,
            message=params.message,
            recoverable=params.recoverable,
        )


__all__ = [
    "BackgroundResumeParams",
    "schedule_background_resume",
]
