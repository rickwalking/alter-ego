"""Validation and access-control helpers for editorial workflow HTTP routes."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.api.routes.carousels.editorial_workflow_routes_sanitize import (
    sanitize_structured_feedback,
)
from rag_backend.api.schemas.carousel_workflow import EditorialWorkflowResumeRequest
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_service_helpers import (
    RevisionCapValidationContext,
    validate_content_approve_persona_score,
    validate_content_approve_presentation,
    validate_revision_cap,
)
from rag_backend.application.services.carousel.presentation_review_edits import (
    edited_slides_block_approval,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.notification_service import NotificationService
from rag_backend.application.services.optimistic_lock_service import (
    CarouselVersionBumpParams,
    OptimisticLockService,
)
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.carousel_workflow import (
    ERR_EDITED_SLIDES_CONTENT_ONLY,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_PRESENTATION_VALIDATION_BLOCKED,
    ERR_RESUME_ALREADY_IN_PROGRESS,
    ERR_REVISE_FEEDBACK_REQUIRED,
    ERR_REVISION_CAP_EXCEEDED,
    ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY,
    ERR_UNSUPPORTED_REVIEW_ACTION,
    PHASE_CONTENT,
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_IN_PROGRESS,
    RESUME_ROUTE_SUPPORTED_ACTIONS,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.constants.persona import ERR_PERSONA_NOT_FOUND
from rag_backend.domain.constants.workflow_validation import ERR_NOT_ASSIGNED_REVIEWER
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.database.models import PersonaProfileModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.user import UserModel


async def load_persona(
    db: AsyncSession, persona_id: str | None
) -> PersonaProfile | None:
    """Load persona profile or raise when the id is invalid."""
    if persona_id is None:
        return None
    model = await db.get(PersonaProfileModel, persona_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_PERSONA_NOT_FOUND,
        )
    return model.to_entity()


def validate_resume_action(body: EditorialWorkflowResumeRequest) -> str:
    """Validate resume action and feedback; return sanitized feedback."""
    if body.action not in RESUME_ROUTE_SUPPORTED_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_UNSUPPORTED_REVIEW_ACTION,
        )
    safe_feedback = sanitize_llm_input(body.feedback or "")
    if body.action == REVIEW_ACTION_REVISE and not safe_feedback.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_REVISE_FEEDBACK_REQUIRED,
        )
    return safe_feedback


def ensure_resume_reviewer_access(
    project: CarouselProjectModel,
    current_user: UserModel,
) -> None:
    """Reject resume when the caller is not the assigned reviewer."""
    if not project.assigned_reviewer_id:
        return
    if project.assigned_reviewer_id == current_user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERR_NOT_ASSIGNED_REVIEWER,
    )


def ensure_resume_not_in_progress(
    project: CarouselProjectModel,
    workflow_state: CarouselWorkflowState | None,
) -> None:
    """Reject resume when workflow is already running."""
    if project.phase_status == PHASE_STATUS_IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_RESUME_ALREADY_IN_PROGRESS,
        )
    if workflow_state is None:
        return
    if str(workflow_state.get("phase_status", "")) != PHASE_STATUS_IN_PROGRESS:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ERR_RESUME_ALREADY_IN_PROGRESS,
    )


async def validate_resume_workflow_gates(
    body: EditorialWorkflowResumeRequest,
    workflow_state: CarouselWorkflowState | None,
    *,
    db: AsyncSession,
    project_id: str,
    project_title: str,
) -> None:
    """Validate revision cap and persona score before accepting resume."""
    if workflow_state is None:
        return
    if body.action == REVIEW_ACTION_REVISE:
        try:
            await validate_revision_cap(
                workflow_state,
                RevisionCapValidationContext(
                    project_id=project_id,
                    project_title=project_title,
                    db=db,
                    notifications=NotificationService(),
                ),
            )
        except ValueError as exc:
            if str(exc) == ERR_REVISION_CAP_EXCEEDED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=ERR_REVISION_CAP_EXCEEDED,
                ) from None
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERR_INVALID_REQUEST,
            ) from None
    if body.action != REVIEW_ACTION_APPROVE:
        return
    try:
        validate_content_approve_persona_score(workflow_state)
        _validate_approve_presentation_with_edits(body, workflow_state)
    except ValueError as exc:
        if str(exc) == ERR_PERSONA_SCORE_TOO_LOW:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=ERR_PERSONA_SCORE_TOO_LOW,
            ) from None
        if str(exc) == ERR_PRESENTATION_VALIDATION_BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=ERR_PRESENTATION_VALIDATION_BLOCKED,
            ) from None
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None


def _validate_approve_presentation_with_edits(
    body: EditorialWorkflowResumeRequest,
    workflow_state: CarouselWorkflowState,
) -> None:
    """Validate presentation for approve, preferring submitted edits when present."""
    sanitized = sanitize_structured_feedback(body.structured_feedback)
    edited = (
        sanitized.get(STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY)
        if sanitized is not None
        else None
    )
    if isinstance(edited, list) and edited:
        edited_dicts = [slide for slide in edited if isinstance(slide, dict)]
        if edited_slides_block_approval(workflow_state, edited_dicts):
            raise ValueError(ERR_PRESENTATION_VALIDATION_BLOCKED)
        return
    validate_content_approve_presentation(workflow_state)


async def bump_resume_lock_version(
    db: AsyncSession,
    project_id: str,
    expected_version: int,
) -> int:
    """Validate optimistic lock and return the new lock version."""
    lock_service = OptimisticLockService()
    try:
        return await lock_service.bump_carousel_version(
            db,
            CarouselVersionBumpParams(
                project_id=project_id,
                expected_version=expected_version,
            ),
        )
    except ValueError as exc:
        if str(exc) == ERR_VERSION_CONFLICT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ERR_VERSION_CONFLICT,
            ) from None
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None


async def ensure_structured_feedback_allowed(
    service: EditorialWorkflowService,
    project_id: str,
    body: EditorialWorkflowResumeRequest,
) -> None:
    """Reject structured feedback fields submitted outside their allowed phase."""
    feedback = body.structured_feedback
    if feedback is None:
        return
    checkpoint_phase = await service.read_checkpoint_phase(project_id)
    has_final_review_fields = bool(feedback.target_phase or feedback.edited_text)
    if has_final_review_fields and checkpoint_phase != PHASE_FINAL_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY,
        )
    if feedback.edited_localized_slides and checkpoint_phase != PHASE_CONTENT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_EDITED_SLIDES_CONTENT_ONLY,
        )


__all__ = [
    "bump_resume_lock_version",
    "ensure_resume_not_in_progress",
    "ensure_resume_reviewer_access",
    "ensure_structured_feedback_allowed",
    "load_persona",
    "validate_resume_action",
    "validate_resume_workflow_gates",
]
