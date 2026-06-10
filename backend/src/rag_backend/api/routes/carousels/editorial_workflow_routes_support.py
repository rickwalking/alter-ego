"""Shared helpers for editorial workflow HTTP routes."""

from __future__ import annotations

from fastapi import Request

from rag_backend.api.routes.carousels.editorial_workflow_routes_response import (
    build_workflow_state_response,
)
from rag_backend.api.routes.carousels.editorial_workflow_routes_sanitize import (
    sanitize_structured_feedback,
)
from rag_backend.api.routes.carousels.editorial_workflow_routes_validate import (
    bump_resume_lock_version,
    ensure_resume_not_in_progress,
    ensure_resume_reviewer_access,
    ensure_structured_feedback_allowed,
    load_persona,
    validate_resume_action,
    validate_resume_workflow_gates,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
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


__all__ = [
    "build_editorial_workflow_service",
    "build_workflow_state_response",
    "bump_resume_lock_version",
    "ensure_resume_not_in_progress",
    "ensure_resume_reviewer_access",
    "ensure_structured_feedback_allowed",
    "load_persona",
    "sanitize_structured_feedback",
    "validate_resume_action",
    "validate_resume_workflow_gates",
]
