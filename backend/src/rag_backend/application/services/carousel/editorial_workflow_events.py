"""Workflow event emission helpers for editorial carousel workflow."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import REVIEW_ACTION_APPROVE
from rag_backend.domain.constants.notifications import (
    NOTIFICATION_TYPE_PHASE_APPROVED,
    NOTIFICATION_TYPE_PHASE_REJECTED,
)
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_PROJECT,
    EVENT_SOURCE_WORKFLOW_ENGINE,
    EVENT_TYPE_PROJECT_PHASE_CHANGED,
    EVENT_TYPE_PROJECT_REVIEW_COMPLETED,
    EVENT_TYPE_PROJECT_REVIEW_REQUESTED,
)
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL

from .editorial_workflow_support import ReviewEventEmitContext
from .workflow_state import CarouselWorkflowState


async def emit_phase_event(
    *,
    db: AsyncSession | None,
    event_service: WorkflowEventService | None,
    project_id: str,
    state: CarouselWorkflowState,
    user_id: str,
) -> None:
    if db is None or event_service is None:
        return
    await event_service.emit(
        db,
        event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
        aggregate_id=project_id,
        aggregate_type=AGGREGATE_TYPE_PROJECT,
        payload={
            "phase": str(state.get("current_phase", "")),
            "phase_status": str(state.get("phase_status", "")),
        },
        metadata={"user_id": user_id, "source": EVENT_SOURCE_WORKFLOW_ENGINE},
    )
    await event_service.emit(
        db,
        event_type=EVENT_TYPE_PROJECT_REVIEW_REQUESTED,
        aggregate_id=project_id,
        aggregate_type=AGGREGATE_TYPE_PROJECT,
        payload={"phase": str(state.get("current_phase", ""))},
        metadata={"user_id": user_id, "source": EVENT_SOURCE_WORKFLOW_ENGINE},
    )


async def emit_review_event(
    *,
    db: AsyncSession | None,
    event_service: WorkflowEventService | None,
    notification_service: NotificationService,
    ctx: ReviewEventEmitContext,
) -> None:
    if db is None or event_service is None:
        return
    old_phase = str(ctx.prior.get("current_phase", "")) if ctx.prior else ""
    new_phase = str(ctx.state.get("current_phase", ""))
    await event_service.emit(
        db,
        event_type=EVENT_TYPE_PROJECT_REVIEW_COMPLETED,
        aggregate_id=ctx.project_id,
        aggregate_type=AGGREGATE_TYPE_PROJECT,
        payload={
            "action": ctx.action,
            "feedback": ctx.feedback or "",
            "phase": new_phase,
        },
        metadata={
            "reviewer_id": ctx.reviewer_id,
            "source": EVENT_SOURCE_WORKFLOW_ENGINE,
        },
    )
    if old_phase != new_phase:
        await event_service.emit(
            db,
            event_type=EVENT_TYPE_PROJECT_PHASE_CHANGED,
            aggregate_id=ctx.project_id,
            aggregate_type=AGGREGATE_TYPE_PROJECT,
            payload={
                "old_phase": old_phase,
                "phase": new_phase,
                "phase_status": str(ctx.state.get("phase_status", "")),
            },
            metadata={
                "reviewer_id": ctx.reviewer_id,
                "source": EVENT_SOURCE_WORKFLOW_ENGINE,
            },
        )
    notif_type = (
        NOTIFICATION_TYPE_PHASE_APPROVED
        if ctx.action == REVIEW_ACTION_APPROVE
        else NOTIFICATION_TYPE_PHASE_REJECTED
    )
    await notification_service.create_workflow_update(
        db,
        user_id=ctx.reviewer_id,
        notification_type=notif_type,
        title=f"Phase {ctx.action}: {new_phase}",
        body=ctx.feedback or "",
        content_id=ctx.project_id,
        content_type=CONTENT_TYPE_CAROUSEL,
    )
