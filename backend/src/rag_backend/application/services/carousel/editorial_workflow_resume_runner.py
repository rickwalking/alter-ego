"""Background execution for async editorial workflow resume (RW-010-RW-013)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    publish_workflow_sse_updates,
    resolve_background_resume_sse_error_message,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_STATUS_FAILED,
)
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_background_tasks: set[asyncio.Task[None]] = set()


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
            state = await service.resume_workflow(
                project_id=params.project_id,
                action=params.action,
                reviewer_id=params.reviewer_id,
                feedback=params.feedback,
                db=db,
                persona=None,
                project_title=params.project_title,
                structured_feedback=params.structured_feedback,
            )
            await db.commit()
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
                service,
                params.project_id,
                detail,
                recoverable=detail != ERR_REVISION_CAP_EXCEEDED,
            )
        except Exception:
            await db.rollback()
            logger.exception(
                "background_resume_failed",
                project_id=params.project_id,
            )
            await _mark_background_resume_failed(
                service,
                params.project_id,
                ERR_BACKGROUND_RESUME_FAILED,
                recoverable=True,
            )


async def _mark_background_resume_failed(
    service: EditorialWorkflowService,
    project_id: str,
    message: str,
    *,
    recoverable: bool,
) -> None:
    session_factory = get_session_maker()
    async with session_factory() as db:
        project = await db.get(CarouselProjectModel, project_id)
        if project is not None:
            project.phase_status = PHASE_STATUS_FAILED
            await db.commit()
        await service.publish_resume_error_event(
            project_id,
            message=message,
            recoverable=recoverable,
        )


__all__ = [
    "BackgroundResumeParams",
    "schedule_background_resume",
]
