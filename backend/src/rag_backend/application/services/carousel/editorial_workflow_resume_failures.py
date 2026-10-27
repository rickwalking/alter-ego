"""Failure and stuck-resume persistence for editorial workflow resumes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.domain.constants.carousel_run import RUN_FINISHED_REASON_FAILED
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_STUCK,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
)
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.editorial_workflow_service import (
        EditorialWorkflowService,
    )


@dataclass(frozen=True)
class _MarkFailedParams:
    """Inputs for marking a background resume as failed."""

    service: EditorialWorkflowService
    project_id: str
    message: str
    recoverable: bool


@dataclass(frozen=True)
class _RevertContext:
    service: EditorialWorkflowService
    project_id: str
    prior_phase: str
    session_factory: async_sessionmaker[AsyncSession]
    publish: Callable[..., Awaitable[None]]


async def _revert_background_resume_stuck(context: _RevertContext) -> None:
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


async def _mark_background_resume_failed(
    params: _MarkFailedParams,
    session_factory: async_sessionmaker[AsyncSession],
    publish: Callable[..., Awaitable[None]],
) -> None:
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
        await publish(
            params.project_id,
            RUN_FINISHED_REASON_FAILED,
            final_phase_status=PHASE_STATUS_FAILED,
        )


__all__ = [
    "_MarkFailedParams",
    "_RevertContext",
    "_mark_background_resume_failed",
    "_revert_background_resume_stuck",
]
