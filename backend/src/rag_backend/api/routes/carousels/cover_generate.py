"""Generate a slide-1 cover from the owner's library photos with Grok.

Thin HTTP adapter. ``GET /{id}/cover-generations`` returns the caps in use and
the carousel's generations; ``POST /{id}/cover-generations`` checks the
request (confirmed, owner only, own photos, caps), records a pending
generation and runs the Grok Bot job in a tracked background task (202). The
result is picked like any other cover through ``PUT /{id}/cover``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.cover_generation_prompts import cover_edit_prompt
from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter, user_or_address_key
from rag_backend.api.schemas.carousel_cover_generation import (
    CoverGenerationRequest,
    CoverGenerationResponse,
    CoverGenerationsResponse,
)
from rag_backend.application.services.carousel.cover_generation import (
    CoverGenerationError,
    CoverGenerationForbiddenError,
    CoverGenerationRefusedError,
    CoverGenerationService,
    CoverGenerationUsage,
    StartCoverGeneration,
)
from rag_backend.application.services.carousel.cover_generation_tasks import (
    schedule_cover_generation,
)
from rag_backend.domain.constants.cover_generation import (
    ERR_COVER_GENERATION_UNAVAILABLE,
)
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_COVER_GENERATE,
    RATE_LIMIT_USER_STATE,
)
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.models.cover_generation import CoverGeneration
from rag_backend.modules.editorial.public import (
    CarouselAutomationAcl,
    cover_generation_service,
    cover_generation_task,
    cover_run_wiring,
)
from rag_backend.modules.image_bridge import ImageBridgeConfigError

router = APIRouter(tags=["carousels-cover-generation"])

_PATH = "/{project_id}/cover-generations"


@dataclass(frozen=True)
class CoverGenerationContext:
    """The caller, the carousel and the service."""

    user_id: str
    project: CarouselProject
    service: CoverGenerationService


def rate_limited_editor(request: Request, current_user: EditorUser) -> User:
    """The caller, recorded on the request so the rate limit keys on them."""
    setattr(request.state, RATE_LIMIT_USER_STATE, str(current_user.id))
    return current_user.to_entity()


async def get_cover_generation_context(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(rate_limited_editor)],
) -> CoverGenerationContext:
    """404 for an unknown carousel."""
    project = await CarouselAutomationAcl(db).load_project(str(project_id))
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_CAROUSEL_NOT_FOUND
        )
    return CoverGenerationContext(
        user_id=str(current_user.id),
        project=project,
        service=cover_generation_service(db),
    )


def _http_error(error: CoverGenerationError) -> HTTPException:
    if isinstance(error, CoverGenerationForbiddenError):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, CoverGenerationRefusedError):
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_422_UNPROCESSABLE_CONTENT
    return HTTPException(status_code=code, detail=error.code)


def _generation(generation: CoverGeneration) -> CoverGenerationResponse:
    return CoverGenerationResponse(
        id=generation.id,
        status=generation.status.value,
        error_code=generation.error_code,
        asset_id=generation.result_asset_id,
        created_at=generation.created_at,
        completed_at=generation.completed_at,
    )


def _usage(usage: CoverGenerationUsage) -> CoverGenerationsResponse:
    return CoverGenerationsResponse(
        carousel_used=usage.carousel_used,
        carousel_cap=usage.carousel_cap,
        month_used=usage.month_used,
        month_cap=usage.month_cap,
        carousel_attempts=usage.carousel_attempts,
        carousel_attempt_cap=usage.carousel_attempt_cap,
        month_attempts=usage.month_attempts,
        month_attempt_cap=usage.month_attempt_cap,
        generations=[_generation(g) for g in usage.generations],
    )


@router.get(
    _PATH,
    response_model=CoverGenerationsResponse,
    summary="The caps in use and the Grok cover generations of a carousel",
)
async def list_cover_generations(
    ctx: Annotated[CoverGenerationContext, Depends(get_cover_generation_context)],
) -> CoverGenerationsResponse:
    """Owner only; a run lost to a restart is reported as interrupted."""
    try:
        usage = await ctx.service.usage(ctx.project, ctx.user_id)
    except CoverGenerationError as error:
        raise _http_error(error) from error
    return _usage(usage)


@router.post(
    _PATH,
    response_model=CoverGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a slide-1 cover from library photos with Grok",
    responses={
        403: {"description": "Only the carousel's owner can generate"},
        409: {"description": "A generation is running or a cap is reached"},
        503: {"description": ERR_COVER_GENERATION_UNAVAILABLE},
    },
)
@limiter.limit(RATE_LIMIT_COVER_GENERATE, key_func=user_or_address_key)
async def start_cover_generation(
    request: Request,
    body: CoverGenerationRequest,
    ctx: Annotated[CoverGenerationContext, Depends(get_cover_generation_context)],
) -> CoverGenerationResponse:
    """Record a pending generation and run the Grok Bot job in the background."""
    try:
        wiring = cover_run_wiring(cover_edit_prompt)
    except ImageBridgeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERR_COVER_GENERATION_UNAVAILABLE,
        ) from exc
    command = StartCoverGeneration(
        project=ctx.project,
        user_id=ctx.user_id,
        photo_ids=tuple(body.photo_ids),
        prompt=body.prompt,
        confirmed=body.confirmed,
    )
    try:
        run = await ctx.service.start(command)
    except CoverGenerationError as error:
        raise _http_error(error) from error
    schedule_cover_generation(
        cover_generation_task(wiring, run), str(run.generation.id)
    )
    return _generation(run.generation)


__all__ = ["get_cover_generation_context", "rate_limited_editor", "router"]
