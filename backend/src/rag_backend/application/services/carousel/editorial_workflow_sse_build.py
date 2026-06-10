"""SSE event builders and error resolution for editorial workflow."""

from __future__ import annotations

from rag_backend.application.services.carousel.editorial_workflow_sse_constants import (
    SSE_EVENT_ARTIFACT,
    SSE_EVENT_ERROR,
    SSE_EVENT_PHASE_CHANGE,
    SSE_EVENT_PROGRESS,
    SSE_EVENT_REVIEW_REQUIRED,
    SSE_PAYLOAD_FIELD_EVENT,
    SSE_PAYLOAD_FIELD_GATE,
    SSE_PAYLOAD_FIELD_MESSAGE,
    SSE_PAYLOAD_FIELD_RECOVERABLE,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    ERR_WORKFLOW_PHASE_FAILED,
    WORKFLOW_ARTIFACT_FIELD_DATA,
    WORKFLOW_ARTIFACT_FIELD_TYPE,
    WORKFLOW_ERROR_KEY,
)


def build_workflow_event(event_type: str, **payload: object) -> dict[str, object]:
    """Build a workflow SSE payload with a normalized event field."""
    return {SSE_PAYLOAD_FIELD_EVENT: event_type, **payload}


def build_phase_change_event(
    project_id: str,
    phase: str,
    phase_status: str,
) -> dict[str, object]:
    """Build a normalized phase_change SSE payload."""
    return build_workflow_event(
        SSE_EVENT_PHASE_CHANGE,
        project_id=project_id,
        phase=phase,
        phase_status=phase_status,
    )


def build_progress_event(
    project_id: str,
    phase: str,
    phase_progress: dict[str, object],
) -> dict[str, object]:
    """Build a normalized progress SSE payload with nested phase_progress."""
    return build_workflow_event(
        SSE_EVENT_PROGRESS,
        project_id=project_id,
        phase=phase,
        phase_progress=phase_progress,
    )


def build_review_gate_payload(state: CarouselWorkflowState) -> dict[str, object]:
    """Build a review gate snapshot for SSE consumers."""
    from rag_backend.application.services.carousel.presentation_review import (
        resolve_presentation_review_from_state,
    )

    review = resolve_presentation_review_from_state(state)
    return {
        "current_phase": str(state.get("current_phase", "")),
        "phase_status": str(state.get("phase_status", "")),
        "research_findings": list(state.get("research_findings") or []),
        "outline": list(state.get("outline") or []),
        "slide_drafts": list(state.get("slide_drafts") or []),
        "image_assets": [str(asset) for asset in (state.get("image_assets") or [])],
        "design_applied": bool(state.get("design_applied")),
        "persona_scores": (
            dict(state.get("persona_scores"))
            if isinstance(state.get("persona_scores"), dict)
            else {}
        ),
        "rubric_scores": (
            dict(state.get("rubric_scores"))
            if isinstance(state.get("rubric_scores"), dict)
            else {}
        ),
        "caption": str(state.get("caption")) if state.get("caption") else None,
        "blog_markdown": (
            str(state.get("blog_markdown")) if state.get("blog_markdown") else None
        ),
        **review,
    }


def build_review_required_event(
    project_id: str,
    phase: str,
    phase_status: str,
    gate_payload: dict[str, object],
) -> dict[str, object]:
    """Build a review_required SSE payload."""
    return build_workflow_event(
        SSE_EVENT_REVIEW_REQUIRED,
        project_id=project_id,
        phase=phase,
        phase_status=phase_status,
        **{SSE_PAYLOAD_FIELD_GATE: gate_payload},
    )


def build_error_event(
    project_id: str,
    phase: str,
    message: str,
    *,
    recoverable: bool = False,
) -> dict[str, object]:
    """Build an error SSE payload."""
    return build_workflow_event(
        SSE_EVENT_ERROR,
        project_id=project_id,
        phase=phase,
        **{
            SSE_PAYLOAD_FIELD_MESSAGE: message,
            SSE_PAYLOAD_FIELD_RECOVERABLE: recoverable,
        },
    )


def build_artifact_event(
    project_id: str,
    phase: str,
    artifact_type: str,
    data: object,
) -> dict[str, object]:
    """Build an artifact SSE payload for incremental gate updates."""
    return build_workflow_event(
        SSE_EVENT_ARTIFACT,
        project_id=project_id,
        phase=phase,
        **{
            WORKFLOW_ARTIFACT_FIELD_TYPE: artifact_type,
            WORKFLOW_ARTIFACT_FIELD_DATA: data,
        },
    )


CLIENT_SAFE_SSE_ERROR_MESSAGES: frozenset[str] = frozenset({
    ERR_INVALID_JSON,
    ERR_WORKFLOW_PHASE_FAILED,
    ERR_REVISION_CAP_EXCEEDED,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_BACKGROUND_RESUME_FAILED,
})


def resolve_workflow_sse_error_message(state: CarouselWorkflowState) -> str:
    """Map workflow failure state to a client-safe SSE error message."""
    raw_error = state.get(WORKFLOW_ERROR_KEY) or state.get("error_message")
    if isinstance(raw_error, str) and raw_error in CLIENT_SAFE_SSE_ERROR_MESSAGES:
        return raw_error
    return ERR_WORKFLOW_PHASE_FAILED


def resolve_background_resume_sse_error_message(detail: str) -> str:
    """Map background resume failures to client-safe SSE error messages."""
    if detail in CLIENT_SAFE_SSE_ERROR_MESSAGES:
        return detail
    return ERR_BACKGROUND_RESUME_FAILED


__all__ = [
    "CLIENT_SAFE_SSE_ERROR_MESSAGES",
    "build_artifact_event",
    "build_error_event",
    "build_phase_change_event",
    "build_progress_event",
    "build_review_gate_payload",
    "build_review_required_event",
    "build_workflow_event",
    "resolve_background_resume_sse_error_message",
    "resolve_workflow_sse_error_message",
]
