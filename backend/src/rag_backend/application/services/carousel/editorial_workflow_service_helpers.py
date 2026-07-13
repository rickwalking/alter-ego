"""Resume validation, feedback learning, and SSE streaming helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EventParams,
    PhaseFeedbackPersistParams,
    build_phase_change_event,
    build_progress_event,
    build_review_gate_payload,
    build_review_required_event,
    persist_phase_feedback,
)
from rag_backend.application.services.carousel.presentation_review import (
    has_blocking_presentation_validation,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    get_workflow_sse_hub,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.notification_service import (
    NotificationService,
    RevisionCapEscalationParams,
)
from rag_backend.domain.constants.carousel_workflow import (
    DEFAULT_REVISION_CAP_PER_PHASE,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_PRESENTATION_VALIDATION_BLOCKED,
    ERR_REVISION_CAP_EXCEEDED,
    FINAL_REVIEW_SEND_BACK_PHASES,
    PERSONA_SCORE_OVERALL_KEY,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
    SLIDE_DRAFT_TEXT_KEY,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
    STRUCTURED_FEEDBACK_EDITED_TEXT_KEY,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.domain.models.persona import PersonaProfile


@dataclass(frozen=True)
class RevisionCapValidationContext:
    """Inputs for revision cap validation during workflow resume."""

    project_id: str
    project_title: str
    db: AsyncSession | None = None
    notifications: NotificationService | None = None
    # AE-0310: sanitized structured feedback so the cap check is target-aware
    # (send-backs consume the TARGET phase's budget; edits consume none).
    structured_feedback: dict[str, object] | None = None


@dataclass(frozen=True)
class FeedbackCorrectionContext:
    """Inputs for persisting reviewer feedback corrections."""

    project_id: str
    prior: CarouselWorkflowState
    feedback: str | None
    persona: PersonaProfile | None = None
    structured_feedback: dict[str, object] | None = None
    db: AsyncSession | None = None


class ResumeContext(TypedDict):
    """Context for preparing a workflow resume."""

    orchestrator: CarouselEditorialOrchestrator
    project_id: str
    action: str
    prior: CarouselWorkflowState | None
    feedback: str | None
    structured_feedback: dict[str, object] | None


def validate_content_approve_persona_score(prior: CarouselWorkflowState) -> None:
    """Reject content approval when persona voice match is below threshold."""
    current_phase = str(prior.get("current_phase", ""))
    if current_phase != PHASE_CONTENT:
        return
    persona_scores = prior.get("persona_scores") or {}
    if not isinstance(persona_scores, dict) or not persona_scores:
        return
    min_score = min(
        float(value.get(PERSONA_SCORE_OVERALL_KEY, 0))
        if isinstance(value, dict)
        else float(value)
        for value in persona_scores.values()
    )
    if min_score < VOICE_MATCH_MIN_SCORE:
        raise ValueError(ERR_PERSONA_SCORE_TOO_LOW)


def validate_content_approve_presentation(prior: CarouselWorkflowState) -> None:
    """Reject content approval when blocking presentation violations exist."""
    current_phase = str(prior.get("current_phase", ""))
    if current_phase != PHASE_CONTENT:
        return
    if has_blocking_presentation_validation(prior):
        raise ValueError(ERR_PRESENTATION_VALIDATION_BLOCKED)


def _has_edited_localized_slides(
    structured_feedback: dict[str, object] | None,
) -> bool:
    """True when the resume submission carries non-empty edited slides."""
    if not isinstance(structured_feedback, dict):
        return False
    edited = structured_feedback.get(STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY)
    return isinstance(edited, list) and bool(edited)


def resolve_revision_cap_phase(
    prior: CarouselWorkflowState,
    structured_feedback: dict[str, object] | None,
) -> str | None:
    """Return the phase whose revision budget a revise consumes (AE-0310).

    Accounting rule (pinned by the ticket):
    - a send-back charges the TARGET phase — the phase whose LLM re-runs
      (fixes the pre-existing check/increment divergence: the increment
      already bumped the target while the check read the current phase);
    - an ``edited_localized_slides`` submission charges NO phase — human
      edits are uncapped, the guaranteed escape hatch;
    - a plain design revise while a blocking validation report exists charges
      NO phase — it is a provable content no-op (re-validate + re-interrupt);
    - any other plain revise charges the current phase.
    """
    target = _resume_target_phase(structured_feedback)
    if target in FINAL_REVIEW_SEND_BACK_PHASES:
        return target
    if _has_edited_localized_slides(structured_feedback):
        return None
    current = str(prior.get("current_phase", ""))
    if current == PHASE_DESIGN and has_blocking_presentation_validation(prior):
        return None
    return current


async def validate_revision_cap(
    prior: CarouselWorkflowState,
    ctx: RevisionCapValidationContext,
) -> None:
    """Reject revise when the charged phase's revision cap is exceeded.

    Target-aware (AE-0310): send-backs evaluate the TARGET phase's counter,
    plain revises the current phase's; uncapped submissions skip the check.
    """
    phase = resolve_revision_cap_phase(prior, ctx.structured_feedback)
    if phase is None:
        return
    revision_counts = prior.get("revision_count") or {}
    current_count = (
        int(revision_counts.get(phase, 0)) if isinstance(revision_counts, dict) else 0
    )
    if current_count < DEFAULT_REVISION_CAP_PER_PHASE:
        return
    if ctx.db is not None and ctx.notifications is not None:
        await ctx.notifications.create_revision_cap_escalation(
            ctx.db,
            RevisionCapEscalationParams(
                content_id=ctx.project_id,
                content_type=CONTENT_TYPE_CAROUSEL,
                phase=phase,
                title=ctx.project_title or ctx.project_id,
            ),
        )
    raise ValueError(ERR_REVISION_CAP_EXCEEDED)


async def record_feedback_correction(
    _orchestrator: CarouselEditorialOrchestrator,
    ctx: FeedbackCorrectionContext,
) -> None:
    """Persist reviewer edits for feedback learning (CP-007)."""
    if ctx.db is None or ctx.persona is None or not ctx.feedback:
        return
    # AE-0288: on a final-review send-back the correction belongs to the target
    # phase (e.g. content), not the current checkpoint phase (final_review).
    target = _resume_target_phase(ctx.structured_feedback)
    phase = (
        target
        if target in FINAL_REVIEW_SEND_BACK_PHASES
        else str(ctx.prior.get("current_phase", ""))
    )
    original = _feedback_original_text(ctx.prior, phase)
    corrected = _feedback_corrected_text(ctx.feedback, ctx.structured_feedback)
    if corrected.strip() == original.strip():
        return
    from rag_backend.agents.feedback_learning import FeedbackLearningLoop
    from rag_backend.infrastructure.external.openai_embeddings import (  # type: ignore[attr-defined]
        OpenAIEmbeddings,
    )

    feedback_loop = FeedbackLearningLoop(session=ctx.db, embeddings=OpenAIEmbeddings())
    await feedback_loop.record_correction(
        _original=original,
        _corrected=corrected,
        _context=phase,
        _persona_id=str(ctx.persona.id),
        project_id=ctx.project_id,
    )


def _feedback_original_text(prior: CarouselWorkflowState, phase: str) -> str:
    if phase != PHASE_CONTENT:
        return ""
    slide_drafts = prior.get("slide_drafts") or []
    if not isinstance(slide_drafts, list) or not slide_drafts:
        return ""
    first_slide = slide_drafts[0]
    if not isinstance(first_slide, dict):
        return ""
    return str(first_slide.get(SLIDE_DRAFT_TEXT_KEY, ""))


def _feedback_corrected_text(
    feedback: str,
    structured_feedback: dict[str, object] | None,
) -> str:
    if structured_feedback is None:
        return feedback
    edited = structured_feedback.get(STRUCTURED_FEEDBACK_EDITED_TEXT_KEY)
    if isinstance(edited, str) and edited.strip():
        return edited
    return feedback


async def prepare_resume_workflow(
    context: ResumeContext,
) -> None:
    """Validate resume preconditions and persist revise feedback."""
    prior = context["prior"]
    if prior is None:
        return
    action = context["action"]
    if action == REVIEW_ACTION_APPROVE:
        validate_content_approve_persona_score(prior)
        validate_content_approve_presentation(prior)
    if action == REVIEW_ACTION_REVISE:
        structured = context.get("structured_feedback")
        await persist_phase_feedback(
            context["orchestrator"].engine,
            PhaseFeedbackPersistParams(
                project_id=context["project_id"],
                prior=prior,
                feedback=context["feedback"],
                target_phase=_resume_target_phase(structured),
                # AE-0310: increment only when a phase budget is charged.
                count_revision=resolve_revision_cap_phase(prior, structured)
                is not None,
            ),
        )


def _resume_target_phase(
    structured_feedback: dict[str, object] | None,
) -> str | None:
    """Extract a final-review send-back ``target_phase`` from structured feedback."""
    if not isinstance(structured_feedback, dict):
        return None
    target = structured_feedback.get(STRUCTURED_FEEDBACK_TARGET_PHASE_KEY)
    return target if isinstance(target, str) else None


async def stream_workflow_phase_updates(
    orchestrator: CarouselEditorialOrchestrator,
    project_id: str,
    *,
    phase_progress: dict[str, object] | None = None,
) -> AsyncIterator[dict[str, object]]:
    """Yield initial workflow snapshot events, then hub updates."""
    state = await orchestrator.get_state(project_id)
    if state is None:
        return
    current_phase = str(state.get("current_phase", ""))
    if not current_phase:
        return
    yield build_phase_change_event(
        project_id,
        current_phase,
        str(state.get("phase_status", "")),
    )

    resolved_progress = phase_progress
    if resolved_progress is None:
        raw_progress = state.get("phase_progress")
        if isinstance(raw_progress, dict):
            resolved_progress = raw_progress

    if resolved_progress:
        yield build_progress_event(project_id, current_phase, resolved_progress)

    phase_status = str(state.get("phase_status", ""))
    if phase_status == PHASE_STATUS_AWAITING_HUMAN:
        yield build_review_required_event(
            EventParams(project_id=project_id, phase=current_phase),
            phase_status=phase_status,
            gate_payload=build_review_gate_payload(state),
        )

    hub = get_workflow_sse_hub()
    async for event in hub.listen(project_id):
        yield event


__all__ = [
    "FeedbackCorrectionContext",
    "ResumeContext",
    "RevisionCapValidationContext",
    "prepare_resume_workflow",
    "record_feedback_correction",
    "resolve_revision_cap_phase",
    "stream_workflow_phase_updates",
    "validate_content_approve_persona_score",
    "validate_content_approve_presentation",
    "validate_revision_cap",
]
