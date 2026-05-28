"""Resume validation, feedback learning, and SSE streaming helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    build_phase_change_event,
    build_progress_event,
    build_review_gate_payload,
    build_review_required_event,
    persist_phase_feedback,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    get_workflow_sse_hub,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.notification_service import NotificationService
from rag_backend.domain.constants.carousel_workflow import (
    DEFAULT_REVISION_CAP_PER_PHASE,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    PERSONA_SCORE_OVERALL_KEY,
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
    SLIDE_DRAFT_TEXT_KEY,
    STRUCTURED_FEEDBACK_EDITED_TEXT_KEY,
)
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.domain.models.persona import PersonaProfile


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


async def validate_revision_cap(
    prior: CarouselWorkflowState,
    *,
    db: AsyncSession | None,
    notifications: NotificationService | None,
    project_id: str,
    project_title: str,
) -> None:
    """Reject revise when the per-phase revision cap is exceeded."""
    phase = str(prior.get("current_phase", ""))
    revision_counts = prior.get("revision_count") or {}
    current_count = (
        int(revision_counts.get(phase, 0)) if isinstance(revision_counts, dict) else 0
    )
    if current_count < DEFAULT_REVISION_CAP_PER_PHASE:
        return
    if db is not None and notifications is not None:
        await notifications.create_revision_cap_escalation(
            db,
            content_id=project_id,
            content_type=CONTENT_TYPE_CAROUSEL,
            phase=phase,
            title=project_title or project_id,
        )
    raise ValueError(ERR_REVISION_CAP_EXCEEDED)


async def record_feedback_correction(
    *,
    orchestrator: CarouselEditorialOrchestrator,
    db: AsyncSession | None,
    project_id: str,
    prior: CarouselWorkflowState,
    persona: PersonaProfile | None,
    feedback: str | None,
    structured_feedback: dict[str, object] | None,
) -> None:
    """Persist reviewer edits for feedback learning (CP-007)."""
    if db is None or persona is None or not feedback:
        return
    phase = str(prior.get("current_phase", ""))
    original = ""
    if phase == PHASE_CONTENT:
        slide_drafts = prior.get("slide_drafts") or []
        if isinstance(slide_drafts, list) and slide_drafts:
            first_slide = slide_drafts[0]
            if isinstance(first_slide, dict):
                original = str(first_slide.get(SLIDE_DRAFT_TEXT_KEY, ""))
    corrected = feedback
    if structured_feedback is not None:
        edited = structured_feedback.get(STRUCTURED_FEEDBACK_EDITED_TEXT_KEY)
        if isinstance(edited, str) and edited.strip():
            corrected = edited
    if corrected.strip() == original.strip():
        return
    from rag_backend.agents.feedback_learning import FeedbackLearningLoop
    from rag_backend.infrastructure.external.openai_embeddings import (  # type: ignore[attr-defined]
        OpenAIEmbeddings,
    )

    feedback_loop = FeedbackLearningLoop(session=db, embeddings=OpenAIEmbeddings())
    await feedback_loop.record_correction(
        _original=original,
        _corrected=corrected,
        _context=phase,
        _persona_id=str(persona.id),
        project_id=project_id,
    )


async def prepare_resume_workflow(
    orchestrator: CarouselEditorialOrchestrator,
    project_id: str,
    action: str,
    prior: CarouselWorkflowState | None,
    feedback: str | None,
) -> None:
    """Validate resume preconditions and persist revise feedback."""
    if prior is None:
        return
    if action == REVIEW_ACTION_APPROVE:
        validate_content_approve_persona_score(prior)
    if action == REVIEW_ACTION_REVISE:
        await persist_phase_feedback(
            orchestrator.engine,
            project_id,
            prior,
            feedback,
        )


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
            project_id,
            current_phase,
            phase_status,
            build_review_gate_payload(state),
        )

    hub = get_workflow_sse_hub()
    async for event in hub.listen(project_id):
        yield event


__all__ = [
    "prepare_resume_workflow",
    "record_feedback_correction",
    "stream_workflow_phase_updates",
    "validate_content_approve_persona_score",
    "validate_revision_cap",
]
