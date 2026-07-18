"""Carousel editorial workflow API routes (AI-004, UI-016 backend).

Thin HTTP/SSE adapters (AE-0110). Each endpoint parses + access-checks the
request at the edge, resolves the editorial workflow ENGINE through the
module-level ``build_editorial_workflow_service`` seam (kept module-level so the
AE-0106 safety-net stub still overrides it), delegates the engine orchestration +
the workflow-owned commit to the editorial :class:`EditorialWorkflowHandlers`
(via the editorial facade), and maps the result to the response. The routes no
longer import the carousel ORM, never resolve the global container, and never
call ``db.commit()`` directly — the WO writes commit through the AE-0107 single
write owner via the platform Unit of Work, inside the handlers.

The LangGraph checkpoint identifiers (``thread_id == project_id``), the
``CarouselWorkflowState`` schema, and the interrupt payloads are unchanged: the
handlers WRAP the existing engine built here, they do not replace it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

import structlog
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
from rag_backend.api.dependencies.editorial import get_editorial_workflow_handlers
from rag_backend.api.dependencies.feature_flags import RequireEditorialWorkflow
from rag_backend.api.dependencies.resource_access import validate_reviewer_user
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.editorial_workflow_routes_response import (
    RunMetadataInput,
    apply_run_metadata,
)
from rag_backend.api.routes.carousels.editorial_workflow_routes_support import (
    build_editorial_workflow_service,
    build_editorial_workflow_state_response,
    bump_resume_lock_version,
    ensure_no_artifact_mutation_in_progress,
    ensure_resume_not_in_progress,
    ensure_resume_reviewer_access,
    ensure_structured_feedback_allowed,
    load_persona,
    sanitize_structured_feedback,
    validate_resume_action,
    validate_resume_workflow_gates,
)
from rag_backend.api.routes.carousels.editorial_workflow_routes_validate import (
    _ResumeGateContext,
)
from rag_backend.api.schemas.carousel_conflict import CarouselConflictResponse
from rag_backend.api.schemas.carousel_workflow import (
    EditorialWorkflowResumeAcceptedResponse,
    EditorialWorkflowResumeRequest,
    EditorialWorkflowStartRequest,
    EditorialWorkflowStateResponse,
)
from rag_backend.application.services.carousel.carousel_run_stage import get_run_stage
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
from rag_backend.application.services.carousel.provider_errors import (
    classify_provider_error,
)
from rag_backend.application.services.carousel.workflow_sse_hub import (
    WorkflowSseSubscriberLimitError,
    get_workflow_sse_hub,
)
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    ERR_PROVIDER_RATE_LIMITED,
    ERR_RESEARCH_SYNTHESIS_FAILED,
    ERR_WORKFLOW_SSE_SUBSCRIBER_LIMIT,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_AI_ENDPOINTS,
    RATE_LIMIT_SSE_STREAM,
)
from rag_backend.domain.constants.workflow_validation import ERR_SELF_REVIEW
from rag_backend.modules.editorial import (
    EditorialWorkflowHandlers,
    StartWorkflowCommand,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    tags=["carousel_editorial_workflow"], dependencies=[RequireEditorialWorkflow]
)

EditorialWorkflowHandlersDep = Annotated[
    EditorialWorkflowHandlers, Depends(get_editorial_workflow_handlers)
]


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
    handlers: EditorialWorkflowHandlersDep,
) -> EditorialWorkflowStateResponse:
    """Return persisted workflow state for UI polling."""
    project = await get_carousel_project_for_workflow_user(db, project_id, current_user)
    engine = build_editorial_workflow_service(request)
    view = await handlers.get_state(engine, str(project_id))
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_INVALID_REQUEST,
        )
    response = build_editorial_workflow_state_response(
        dict(view.state),
        phase_progress=view.phase_progress,
        lock_version=view.lock_version,
    )
    # AE-0315: run metadata (banner reconstruction on reload) — only attached
    # while the merged state reports in_progress.
    return apply_run_metadata(
        response,
        RunMetadataInput(
            run_started_at=project.run_started_at,
            run_stage=get_run_stage(str(project_id)),
        ),
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
    handlers: EditorialWorkflowHandlersDep,
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
    engine = build_editorial_workflow_service(request)
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
        view = await handlers.start(
            engine,
            StartWorkflowCommand(
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
            ),
        )
    except ValueError as exc:
        # AE-0318: this catch used to swallow the engine error unlogged with a
        # generic detail, which made prod synthesis failures undiagnosable. The
        # synthesis-specific detail is scoped to the synthesis parse error; any
        # other engine ValueError keeps the legacy generic detail (but is now
        # logged too).
        logger.exception(
            "workflow_start_failed",
            project_id=str(project_id),
            error=str(exc),
        )
        detail = (
            ERR_RESEARCH_SYNTHESIS_FAILED
            if str(exc) == ERR_INVALID_JSON
            else ERR_INVALID_REQUEST
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from None
    except Exception as exc:
        # AE-0319: a provider outage/rate-limit during the synchronous start
        # (observed live: OpenCode Go 429 GoUsageLimitError) must surface as a
        # structured retryable error, not a generic 500. Non-provider errors
        # re-raise unchanged.
        provider_detail = classify_provider_error(exc)
        if provider_detail is None:
            raise
        logger.exception(
            "workflow_start_provider_error",
            project_id=str(project_id),
            detail=provider_detail,
            error=str(exc),
        )
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if provider_detail == ERR_PROVIDER_RATE_LIMITED
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(
            status_code=status_code,
            detail=provider_detail,
        ) from None
    return build_editorial_workflow_state_response(
        dict(view.state),
        phase_progress=view.phase_progress,
        lock_version=view.lock_version,
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
            "description": (
                "Typed conflict: run in progress, version conflict, revision "
                "cap exceeded, or artifact mutation in progress (AE-0316)"
            ),
            "model": CarouselConflictResponse,
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
    handlers: EditorialWorkflowHandlersDep,
) -> JSONResponse:
    """Accept human review and resume workflow asynchronously (RW-010)."""
    project = await get_carousel_project_for_workflow_user(db, project_id, current_user)
    safe_feedback = validate_resume_action(body)
    ensure_resume_reviewer_access(project, current_user)
    engine = build_editorial_workflow_service(request)
    workflow_state = await engine.get_workflow_state(str(project_id))
    ensure_resume_not_in_progress(project, workflow_state)
    await ensure_no_artifact_mutation_in_progress(db, str(project_id))
    await validate_resume_workflow_gates(
        body,
        workflow_state,
        ctx=_ResumeGateContext(
            db=db, project_id=str(project_id), project_title=project.topic
        ),
    )
    new_lock_version = await bump_resume_lock_version(
        db,
        str(project_id),
        body.expected_version,
    )
    await ensure_structured_feedback_allowed(engine, str(project_id), body)
    current_phase = await handlers.mark_resume_in_progress(engine, str(project_id))
    schedule_background_resume(
        engine,
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
    handlers: EditorialWorkflowHandlersDep,
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
    engine = build_editorial_workflow_service(request)

    async def event_generator() -> AsyncIterator[str]:
        event_id = 0
        try:
            async for payload in handlers.stream_phase_updates(
                engine,
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
