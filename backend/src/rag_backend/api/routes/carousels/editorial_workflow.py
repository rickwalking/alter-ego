"""Carousel editorial workflow API routes (AI-004, UI-016 backend)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.api.constants import MEDIA_TYPE_STREAM
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.feature_flags import RequireEditorialWorkflow
from rag_backend.api.dependencies.resource_access import (
    get_carousel_project_for_user,
    validate_reviewer_user,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.carousel_workflow import (
    EditorialWorkflowResumeRequest,
    EditorialWorkflowStartRequest,
    EditorialWorkflowStateResponse,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AI_ENDPOINTS, RATE_LIMIT_SSE_STREAM
from rag_backend.domain.constants.workflow_validation import ERR_SELF_REVIEW
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.models import PersonaProfileModel
from rag_backend.infrastructure.events.factory import get_event_publisher

router = APIRouter(tags=["carousel_editorial_workflow"], dependencies=[RequireEditorialWorkflow])


def _build_service(request: Request) -> EditorialWorkflowService:
    container = get_container()
    checkpointer = getattr(request.app.state, "carousel_checkpointer", None)
    llm = container.llm_service().chat_model
    settings = get_settings()
    publisher = get_event_publisher(settings.redis_url or None)
    events = WorkflowEventService(publisher)
    return EditorialWorkflowService(llm=llm, checkpointer=checkpointer, event_service=events)


def _state_response(state: dict[str, object]) -> EditorialWorkflowStateResponse:
    return EditorialWorkflowStateResponse(
        project_id=str(state.get("project_id", "")),
        current_phase=str(state.get("current_phase", "")),
        phase_status=str(state.get("phase_status", "")),
        research_findings=list(state.get("research_findings") or []),
        outline=list(state.get("outline") or []),
        slide_drafts=list(state.get("slide_drafts") or []),
        status=str(state.get("status", "draft")),
    )


async def _load_persona(db: AsyncSession, persona_id: str | None) -> PersonaProfile | None:
    if persona_id is None:
        return None
    model = await db.get(PersonaProfileModel, persona_id)
    if model is None:
        return None
    return model.to_entity()


@router.post(
    "/carousels/{project_id}/workflow/start",
    response_model=EditorialWorkflowStateResponse,
    summary="Start editorial carousel workflow",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def start_editorial_workflow(
    request: Request,
    project_id: UUID,
    body: EditorialWorkflowStartRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> EditorialWorkflowStateResponse:
    """Run AI synthesis, outline, and draft phases then pause at human gates."""
    await get_carousel_project_for_user(db, project_id, current_user)
    if body.reviewer_id is not None:
        await validate_reviewer_user(db, body.reviewer_id)
        if body.reviewer_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERR_SELF_REVIEW,
            )
    service = _build_service(request)
    persona = await _load_persona(db, body.persona_id)
    sanitized_sources = [
        {
            **source.model_dump(),
            "title": sanitize_llm_input(source.title),
            "content": sanitize_llm_input(source.content),
        }
        for source in body.sources
    ]
    try:
        state = await service.start_workflow(
            project_id=str(project_id),
            workflow_input=EditorialWorkflowStartInput(
                topic=sanitize_llm_input(body.topic),
                audience=sanitize_llm_input(body.audience),
                brief=sanitize_llm_input(body.brief),
                sources=sanitized_sources,
                persona=persona,
                user_id=current_user.id,
                reviewer_id=body.reviewer_id,
            ),
            db=db,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None
    await db.commit()
    return _state_response(dict(state))


@router.post(
    "/carousels/{project_id}/workflow/resume",
    response_model=EditorialWorkflowStateResponse,
    summary="Resume editorial carousel workflow",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def resume_editorial_workflow(
    request: Request,
    project_id: UUID,
    body: EditorialWorkflowResumeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> EditorialWorkflowStateResponse:
    """Resume workflow after human review."""
    await get_carousel_project_for_user(db, project_id, current_user)
    service = _build_service(request)
    safe_feedback = sanitize_llm_input(body.feedback or "")
    state = await service.resume_workflow(
        project_id=str(project_id),
        action=body.action,
        reviewer_id=current_user.id,
        feedback=safe_feedback,
        db=db,
    )
    await db.commit()
    return _state_response(dict(state))


@router.get(
    "/carousels/{project_id}/workflow/stream",
    summary="Stream editorial workflow phase updates",
)
@limiter.limit(RATE_LIMIT_SSE_STREAM)
async def stream_editorial_workflow(
    project_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> StreamingResponse:
    """SSE stream of the current workflow phase for UI-016."""
    await get_carousel_project_for_user(db, project_id, current_user)
    service = _build_service(request)

    async def event_generator() -> AsyncIterator[str]:
        event_id = 0
        async for payload in service.stream_phase_updates(str(project_id)):
            event_id += 1
            yield f"id: {event_id}\nevent: {payload['event']}\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type=MEDIA_TYPE_STREAM)


__all__ = ["router"]
