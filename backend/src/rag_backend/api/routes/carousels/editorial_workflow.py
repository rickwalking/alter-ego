"""Carousel editorial workflow API routes (AI-004, UI-016 backend)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.api.constants import MEDIA_TYPE_STREAM
from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_user,
    get_carousel_project_for_workflow_user,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.feature_flags import RequireEditorialWorkflow
from rag_backend.api.dependencies.resource_access import validate_reviewer_user
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.editorial_workflow_routes_support import (
    build_editorial_workflow_service,
    build_workflow_state_response,
    bump_resume_lock_version,
    ensure_resume_not_in_progress,
    ensure_resume_reviewer_access,
    ensure_structured_feedback_allowed,
    load_persona,
    sanitize_structured_feedback,
    validate_resume_action,
    validate_resume_workflow_gates,
)
from rag_backend.api.schemas.carousel_workflow import (
    EditorialWorkflowResumeAcceptedResponse,
    EditorialWorkflowResumeRequest,
    EditorialWorkflowStartRequest,
    EditorialWorkflowStateResponse,
)
from rag_backend.application.services.carousel.editorial_workflow_resume_runner import (
    BackgroundResumeParams,
    schedule_background_resume,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    SSE_EVENT_KEEPALIVE,
    SSE_PAYLOAD_FIELD_EVENT,
    format_sse_event,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    WorkflowSseSubscriberLimitError,
    get_workflow_sse_hub,
)
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.carousel_workflow import (
    ERR_WORKFLOW_SSE_SUBSCRIBER_LIMIT,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_AI_ENDPOINTS,
    RATE_LIMIT_SSE_STREAM,
)
from rag_backend.domain.constants.workflow_validation import ERR_SELF_REVIEW
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

router = APIRouter(
    tags=["carousel_editorial_workflow"], dependencies=[RequireEditorialWorkflow]
)


@router.get(
    "/carousels/{project_id}/workflow/state",
    response_model=EditorialWorkflowStateResponse,
    summary="Get editorial carousel workflow state",
)
async def get_editorial_workflow_state(
    project_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> EditorialWorkflowStateResponse:
    """Return persisted workflow state for UI polling."""
    project = await get_carousel_project_for_workflow_user(db, project_id, current_user)
    service = build_editorial_workflow_service(request)
    state = await service.get_workflow_state(str(project_id))
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_INVALID_REQUEST,
        )
    project_progress = (
        project.phase_progress if isinstance(project.phase_progress, dict) else None
    )
    return build_workflow_state_response(
        dict(state),
        phase_progress=project_progress,
        lock_version=int(project.lock_version or 1),
    )


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
    service = build_editorial_workflow_service(request)
    persona = await load_persona(db, body.persona_id)
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
    project = await db.get(CarouselProjectModel, str(project_id))
    project_progress = (
        project.phase_progress
        if project is not None and isinstance(project.phase_progress, dict)
        else None
    )
    return build_workflow_state_response(
        dict(state),
        phase_progress=project_progress,
        lock_version=int(project.lock_version or 1) if project is not None else 1,
    )


@router.post(
    "/carousels/{project_id}/workflow/resume",
    response_model=EditorialWorkflowResumeAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resume editorial carousel workflow",
    responses={
        status.HTTP_202_ACCEPTED: {
            "model": EditorialWorkflowResumeAcceptedResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "Resume already in progress or version conflict",
        },
    },
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def resume_editorial_workflow(
    request: Request,
    project_id: UUID,
    body: EditorialWorkflowResumeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> JSONResponse:
    """Accept human review and resume workflow asynchronously (RW-010)."""
    project = await get_carousel_project_for_workflow_user(db, project_id, current_user)
    safe_feedback = validate_resume_action(body)
    ensure_resume_reviewer_access(project, current_user)
    service = build_editorial_workflow_service(request)
    workflow_state = await service.get_workflow_state(str(project_id))
    ensure_resume_not_in_progress(project, workflow_state)
    await validate_resume_workflow_gates(
        body,
        workflow_state,
        db=db,
        project_id=str(project_id),
        project_title=project.topic,
    )
    new_lock_version = await bump_resume_lock_version(
        db,
        str(project_id),
        body.expected_version,
    )
    await ensure_structured_feedback_allowed(service, str(project_id), body)
    current_phase = await service.mark_resume_in_progress(str(project_id), db=db)
    await db.commit()
    schedule_background_resume(
        service,
        BackgroundResumeParams(
            project_id=str(project_id),
            action=body.action,
            reviewer_id=current_user.id,
            feedback=safe_feedback or None,
            project_title=project.topic,
            structured_feedback=sanitize_structured_feedback(body.structured_feedback),
        ),
    )
    payload = EditorialWorkflowResumeAcceptedResponse(
        accepted=True,
        project_id=str(project_id),
        current_phase=current_phase,
        phase_status=PHASE_STATUS_IN_PROGRESS,
        lock_version=new_lock_version,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=payload.model_dump(),
    )


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
    project = await get_carousel_project_for_workflow_user(
        db,
        project_id,
        current_user,
    )
    hub = get_workflow_sse_hub()
    if not hub.can_accept_subscriber(str(project_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ERR_WORKFLOW_SSE_SUBSCRIBER_LIMIT,
        )
    phase_progress = (
        project.phase_progress if isinstance(project.phase_progress, dict) else None
    )
    service = build_editorial_workflow_service(request)

    async def event_generator() -> AsyncIterator[str]:
        event_id = 0
        try:
            async for payload in service.stream_phase_updates(
                str(project_id),
                phase_progress=phase_progress,
            ):
                if payload.get(SSE_PAYLOAD_FIELD_EVENT) == SSE_EVENT_KEEPALIVE:
                    yield ": keepalive\n\n"
                    continue
                event_id += 1
                yield format_sse_event(payload, event_id=event_id)
        except WorkflowSseSubscriberLimitError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ERR_WORKFLOW_SSE_SUBSCRIBER_LIMIT,
            ) from exc

    return StreamingResponse(event_generator(), media_type=MEDIA_TYPE_STREAM)


__all__ = ["router"]
