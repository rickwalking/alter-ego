"""SSE formatting and feedback persistence helpers for editorial workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    ERR_WORKFLOW_PHASE_FAILED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    WORKFLOW_ARTIFACT_FIELD_DATA,
    WORKFLOW_ARTIFACT_FIELD_TYPE,
    WORKFLOW_ARTIFACT_TYPE_DESIGN_APPLIED,
    WORKFLOW_ARTIFACT_TYPE_IMAGE_ASSETS,
    WORKFLOW_ARTIFACT_TYPE_OUTLINE,
    WORKFLOW_ARTIFACT_TYPE_PERSONA_SCORES,
    WORKFLOW_ARTIFACT_TYPE_SLIDE_DRAFTS,
    WORKFLOW_ERROR_KEY,
)
from rag_backend.domain.models.persona import PersonaProfile

SSE_EVENT_PHASE_CHANGE = "phase_change"
SSE_EVENT_PROGRESS = "progress"
SSE_EVENT_REVIEW_REQUIRED = "review_required"
SSE_EVENT_ERROR = "error"
SSE_EVENT_ARTIFACT = "artifact"
SSE_EVENT_KEEPALIVE = "_keepalive"
WORKFLOW_SSE_KEEPALIVE_SECONDS = 30
WORKFLOW_SSE_MAX_SUBSCRIBERS_PER_PROJECT = 10
SSE_PAYLOAD_FIELD_EVENT = "event"
SSE_PAYLOAD_FIELD_GATE = "gate_payload"
SSE_PAYLOAD_FIELD_MESSAGE = "message"
SSE_PAYLOAD_FIELD_RECOVERABLE = "recoverable"

WORKFLOW_ARTIFACT_UPDATE_FIELD_MAP: dict[str, str] = {
    "outline": WORKFLOW_ARTIFACT_TYPE_OUTLINE,
    "slide_drafts": WORKFLOW_ARTIFACT_TYPE_SLIDE_DRAFTS,
    "design_applied": WORKFLOW_ARTIFACT_TYPE_DESIGN_APPLIED,
    "image_assets": WORKFLOW_ARTIFACT_TYPE_IMAGE_ASSETS,
    "persona_scores": WORKFLOW_ARTIFACT_TYPE_PERSONA_SCORES,
}


@dataclass(frozen=True)
class EditorialWorkflowStartInput:
    """Inputs required to start the editorial workflow."""

    topic: str
    audience: str
    brief: str
    sources: list[dict[str, str]]
    persona: PersonaProfile | None = None
    user_id: str = "system"
    reviewer_id: str | None = None


@dataclass(frozen=True)
class ReviewEventEmitContext:
    """Parameters for emitting carousel review workflow events."""

    project_id: str
    action: str
    reviewer_id: str
    feedback: str | None
    prior: CarouselWorkflowState | None
    state: CarouselWorkflowState


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


async def publish_workflow_phase_change(
    project_id: str,
    phase: str,
    phase_status: str,
) -> None:
    """Broadcast a phase_change event to workflow SSE subscribers."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_phase_change_event(project_id, phase, phase_status),
    )


async def publish_workflow_progress(
    project_id: str,
    phase: str,
    phase_progress: dict[str, object],
) -> None:
    """Broadcast a progress event to workflow SSE subscribers."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_progress_event(project_id, phase, phase_progress),
    )


async def publish_workflow_review_required(
    project_id: str,
    state: CarouselWorkflowState,
) -> None:
    """Broadcast a review_required event with gate payload."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    phase = str(state.get("current_phase", ""))
    phase_status = str(state.get("phase_status", ""))
    await get_workflow_sse_hub().publish(
        project_id,
        build_review_required_event(
            project_id,
            phase,
            phase_status,
            build_review_gate_payload(state),
        ),
    )


async def publish_workflow_artifact(
    project_id: str,
    phase: str,
    artifact_type: str,
    data: object,
) -> None:
    """Broadcast an incremental artifact update to workflow SSE subscribers."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_artifact_event(project_id, phase, artifact_type, data),
    )


async def publish_workflow_artifacts_from_updates(
    project_id: str,
    phase: str,
    updates: dict[str, object],
) -> None:
    """Publish artifact SSE events for each generated workflow field."""
    for field, artifact_type in WORKFLOW_ARTIFACT_UPDATE_FIELD_MAP.items():
        if field not in updates:
            continue
        await publish_workflow_artifact(
            project_id,
            phase,
            artifact_type,
            updates[field],
        )


async def publish_workflow_error(
    project_id: str,
    phase: str,
    message: str,
    *,
    recoverable: bool = False,
) -> None:
    """Broadcast a workflow error event."""
    from rag_backend.application.services.carousel.workflow_sse_hub import (
        get_workflow_sse_hub,
    )

    await get_workflow_sse_hub().publish(
        project_id,
        build_error_event(project_id, phase, message, recoverable=recoverable),
    )


async def publish_workflow_sse_updates(
    project_id: str,
    state: CarouselWorkflowState,
) -> None:
    """Publish phase, review, or error events after workflow transitions."""
    phase = str(state.get("current_phase", ""))
    phase_status = str(state.get("phase_status", ""))
    if not phase:
        return
    await publish_workflow_phase_change(project_id, phase, phase_status)
    if phase_status == PHASE_STATUS_AWAITING_HUMAN:
        await publish_workflow_review_required(project_id, state)
    elif phase_status == PHASE_STATUS_FAILED:
        message = resolve_workflow_sse_error_message(state)
        await publish_workflow_error(project_id, phase, message, recoverable=False)


def format_sse_event(
    payload: dict[str, object],
    *,
    event_id: int | None = None,
) -> str:
    """Format a workflow update dict as an SSE frame."""
    event_type = str(payload.get(SSE_PAYLOAD_FIELD_EVENT, SSE_EVENT_PHASE_CHANGE))
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(payload, default=str)}")
    return "\n".join(lines) + "\n\n"


async def read_checkpoint_phase(
    engine: CarouselWorkflowEngine,
    project_id: str,
) -> str:
    """Return current_phase from checkpoint values (ignores pending_next override)."""
    config = engine._run_config(project_id)
    snapshot = await engine._app.aget_state(config)
    if snapshot is None or not isinstance(snapshot.values, dict):
        return ""
    return str(snapshot.values.get("current_phase", ""))


async def persist_phase_feedback(
    engine: CarouselWorkflowEngine,
    project_id: str,
    prior: CarouselWorkflowState,
    feedback: str | None,
) -> None:
    """Store reviewer feedback and increment revision count for the current phase."""
    trimmed = (feedback or "").strip()
    if not trimmed:
        return
    phase = str(prior.get("current_phase", ""))
    if not phase:
        return
    phase_feedback = dict(prior.get("phase_feedback") or {})
    existing = phase_feedback.get(phase, [])
    prior_feedback = existing if isinstance(existing, list) else []
    phase_feedback[phase] = [*prior_feedback, trimmed]
    revision_count = dict(prior.get("revision_count") or {})
    count = int(revision_count.get(phase, 0)) + 1
    revision_count[phase] = count
    await engine.update_state(
        project_id,
        {
            "phase_feedback": phase_feedback,
            "revision_count": revision_count,
        },
    )
