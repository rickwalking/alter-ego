"""Shared helpers for editorial workflow HTTP routes."""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.api.schemas.carousel_workflow import (
    EditorialStructuredFeedback,
    EditorialWorkflowStateResponse,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    FINAL_REVIEW_SEND_BACK_PHASES,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)
from rag_backend.domain.constants.persona import ERR_PERSONA_NOT_FOUND
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.models import PersonaProfileModel
from rag_backend.infrastructure.events.factory import get_event_publisher


def build_editorial_workflow_service(request: Request) -> EditorialWorkflowService:
    """Construct the editorial workflow service for route handlers."""
    container = get_container()
    checkpointer = getattr(request.app.state, "carousel_checkpointer", None)
    llm = container.llm_service().chat_model
    settings = get_settings()
    publisher = get_event_publisher(settings.redis_url or None)
    events = WorkflowEventService(publisher)
    return EditorialWorkflowService(
        llm=llm,
        checkpointer=checkpointer,
        event_service=events,
        image_registry=container.image_provider_registry(),
    )


def sanitize_structured_feedback(
    feedback: EditorialStructuredFeedback | None,
) -> dict[str, object] | None:
    """Sanitize optional structured feedback from resume requests."""
    if feedback is None:
        return None
    raw = feedback.model_dump(exclude_none=True)
    sanitized: dict[str, object] = {}
    target = raw.get(STRUCTURED_FEEDBACK_TARGET_PHASE_KEY)
    if isinstance(target, str) and target in FINAL_REVIEW_SEND_BACK_PHASES:
        sanitized[STRUCTURED_FEEDBACK_TARGET_PHASE_KEY] = target
    edited = raw.get("edited_text")
    if isinstance(edited, str):
        safe_edited = sanitize_llm_input(edited)
        if safe_edited:
            sanitized["edited_text"] = safe_edited
    return sanitized or None


def build_workflow_state_response(
    state: dict[str, object],
    *,
    phase_progress: dict[str, object] | None = None,
    lock_version: int = 1,
) -> EditorialWorkflowStateResponse:
    """Map workflow state dict to API response model."""
    raw_progress = (
        phase_progress if phase_progress is not None else state.get("phase_progress")
    )
    progress = raw_progress if isinstance(raw_progress, dict) else None
    return EditorialWorkflowStateResponse(
        project_id=str(state.get("project_id", "")),
        current_phase=str(state.get("current_phase", "")),
        phase_status=str(state.get("phase_status", "")),
        research_findings=list(state.get("research_findings") or []),
        outline=list(state.get("outline") or []),
        slide_drafts=list(state.get("slide_drafts") or []),
        image_assets=[str(asset) for asset in (state.get("image_assets") or [])],
        design_applied=bool(state.get("design_applied")),
        phase_progress=progress,
        status=str(state.get("status", CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT)),
        lock_version=lock_version,
        workflow_status=str(state.get("workflow_status", "")),
        persona_scores=(
            dict(state.get("persona_scores"))
            if isinstance(state.get("persona_scores"), dict)
            else {}
        ),
        caption=str(state.get("caption")) if state.get("caption") else None,
        blog_markdown=(
            str(state.get("blog_markdown")) if state.get("blog_markdown") else None
        ),
        rubric_scores=(
            dict(state.get("rubric_scores"))
            if isinstance(state.get("rubric_scores"), dict)
            else {}
        ),
        phase_feedback=_string_list_map(state.get("phase_feedback")),
        revision_count=_int_map(state.get("revision_count")),
    )


def _string_list_map(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            result[str(key)] = [str(item) for item in value]
    return result


def _int_map(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in raw.items():
        if isinstance(value, int):
            result[str(key)] = value
        elif isinstance(value, str) and value.isdigit():
            result[str(key)] = int(value)
    return result


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


__all__ = [
    "build_editorial_workflow_service",
    "build_workflow_state_response",
    "load_persona",
    "sanitize_structured_feedback",
]
