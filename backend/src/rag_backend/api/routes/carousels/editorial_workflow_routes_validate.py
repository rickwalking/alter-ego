"""Validation and access-control helpers for editorial workflow HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass

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
    resolve_revision_cap_phase,
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
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
    CONFLICT_CODE_REVISION_CAP_EXCEEDED,
    CONFLICT_CODE_RUN_IN_PROGRESS,
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.carousel_workflow import (
    DESIGN_SEND_BACK_PHASES,
    EDITED_SLIDES_ALLOWED_PHASES,
    ERR_EDITED_SLIDES_PHASE_NOT_ALLOWED,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_PRESENTATION_VALIDATION_BLOCKED,
    ERR_REVISE_FEEDBACK_REQUIRED,
    ERR_REVISION_CAP_EXCEEDED,
    ERR_SEND_BACK_TARGET_NOT_ALLOWED,
    ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY,
    ERR_UNSUPPORTED_REVIEW_ACTION,
    PHASE_DESIGN,
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
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.database.models import PersonaProfileModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    is_carousel_project_lock_held_session,
)


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


def _request_has_edited_slides(body: EditorialWorkflowResumeRequest) -> bool:
    """True when the resume request carries non-empty edited slides."""
    feedback = body.structured_feedback
    return feedback is not None and bool(feedback.edited_localized_slides)


def validate_resume_action(body: EditorialWorkflowResumeRequest) -> str:
    """Validate resume action and feedback; return sanitized feedback."""
    if body.action not in RESUME_ROUTE_SUPPORTED_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_UNSUPPORTED_REVIEW_ACTION,
        )
    safe_feedback = sanitize_llm_input(body.feedback or "")
    # AE-0310: an edited-slides submission is a complete revise on its own —
    # the edits ARE the input, so no feedback text is required for it.
    if (
        body.action == REVIEW_ACTION_REVISE
        and not safe_feedback.strip()
        and not _request_has_edited_slides(body)
    ):
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
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
        )
    if workflow_state is None:
        return
    if str(workflow_state.get("phase_status", "")) != PHASE_STATUS_IN_PROGRESS:
        return
    raise CarouselConflictError(
        CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
    )


async def ensure_no_artifact_mutation_in_progress(
    db: AsyncSession,
    project_id: str,
) -> None:
    """Reject resume while an artifact mutator holds the project lock.

    Closes the two-commit seam (AE-0316/AE-0311): a repair/republish/edit
    holds the session-scoped advisory lock across its full write sequence;
    a resume must not start inside that window. The resume runner never
    acquires the lock itself — it only refuses to start while one is held.
    """
    if not await is_carousel_project_lock_held_session(db, project_id):
        return
    raise CarouselConflictError(
        CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
    )


@dataclass(frozen=True)
class _ResumeGateContext:
    """Bundled context for resume workflow gate validation."""

    db: AsyncSession
    project_id: str
    project_title: str


async def validate_resume_workflow_gates(
    body: EditorialWorkflowResumeRequest,
    workflow_state: CarouselWorkflowState | None,
    *,
    ctx: _ResumeGateContext,
) -> None:
    """Validate revision cap and persona score before accepting resume."""
    if workflow_state is None:
        return
    if body.action == REVIEW_ACTION_REVISE:
        sanitized_feedback = sanitize_structured_feedback(body.structured_feedback)
        try:
            await validate_revision_cap(
                workflow_state,
                RevisionCapValidationContext(
                    project_id=ctx.project_id,
                    project_title=ctx.project_title,
                    db=ctx.db,
                    notifications=NotificationService(),
                    structured_feedback=sanitized_feedback,
                ),
            )
        except ValueError as exc:
            if str(exc) == ERR_REVISION_CAP_EXCEEDED:
                # AE-0310: the conflict names the CHARGED phase (the target on
                # a send-back), consumed by the typed 409 client copy.
                charged_phase = resolve_revision_cap_phase(
                    workflow_state, sanitized_feedback
                )
                raise CarouselConflictError(
                    CarouselConflict.for_code(
                        CONFLICT_CODE_REVISION_CAP_EXCEEDED,
                        phase=charged_phase
                        or str(workflow_state.get("current_phase", "")),
                    )
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
    """Validate optimistic lock via the single write owner and return new version.

    Routes the resume ``lock_version`` compare-and-swap through the AE-0107 write
    owner (which delegates UNCHANGED to ``bump_carousel_version``) so the WO
    concurrency-token bump has a single owner. The 409/400 HTTP mapping is
    preserved byte-identically.
    """
    try:
        return await CarouselProjectWriteOwner(db).bump_resume_lock_version(
            project_id,
            expected_version,
        )
    except ValueError as exc:
        if str(exc) == ERR_VERSION_CONFLICT:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_VERSION_CONFLICT)
            ) from None
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None


def _ensure_target_phase_allowed(target_phase: str, checkpoint_phase: str) -> None:
    """Reject a send-back target the checkpoint phase does not accept (AE-0310)."""
    if checkpoint_phase == PHASE_FINAL_REVIEW:
        return
    if checkpoint_phase == PHASE_DESIGN:
        if target_phase in DESIGN_SEND_BACK_PHASES:
            return
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_SEND_BACK_TARGET_NOT_ALLOWED,
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY,
    )


async def ensure_structured_feedback_allowed(
    service: EditorialWorkflowService,
    project_id: str,
    body: EditorialWorkflowResumeRequest,
) -> None:
    """Reject structured feedback fields submitted outside their allowed phase.

    AE-0310 widened the allowlists: ``edited_localized_slides`` is accepted at
    {content, design, final_review} (uniform apply + re-validate semantics) and
    ``target_phase`` is accepted at design (content only) besides final_review.
    ``edited_text`` stays final-review-only.
    """
    feedback = body.structured_feedback
    if feedback is None:
        return
    checkpoint_phase = await service.read_checkpoint_phase(project_id)
    if feedback.edited_text and checkpoint_phase != PHASE_FINAL_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY,
        )
    if feedback.target_phase:
        _ensure_target_phase_allowed(feedback.target_phase, checkpoint_phase)
    if (
        feedback.edited_localized_slides
        and checkpoint_phase not in EDITED_SLIDES_ALLOWED_PHASES
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_EDITED_SLIDES_PHASE_NOT_ALLOWED,
        )


__all__ = [
    "bump_resume_lock_version",
    "ensure_no_artifact_mutation_in_progress",
    "ensure_resume_not_in_progress",
    "ensure_resume_reviewer_access",
    "ensure_structured_feedback_allowed",
    "load_persona",
    "validate_resume_action",
    "validate_resume_workflow_gates",
]
