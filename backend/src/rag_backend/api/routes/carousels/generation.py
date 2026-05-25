import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
    MEDIA_TYPE_STREAM,
)
from rag_backend.api.dependencies import (
    require_authenticated_user,
    require_editor_or_admin,
)
from rag_backend.api.schemas import (
    CarouselGenerateRequest,
    CarouselStatusResponse,
)
from rag_backend.domain.models import User
from rag_backend.domain.protocols import CarouselAgent, CarouselRepository

from .deps import get_carousel_agent, get_carousel_repo

router = APIRouter()


@router.post(
    "/{project_id}/generate",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
async def generate_carousel(
    project_id: UUID,
    request: CarouselGenerateRequest,
    user: Annotated[User, Depends(require_editor_or_admin)],
    agent: Annotated[CarouselAgent, Depends(get_carousel_agent)],
) -> CarouselStatusResponse:
    """Trigger the full carousel generation pipeline."""
    project = await agent.execute_pipeline(
        project_id,
        seed_urls=request.sources,
    )
    return CarouselStatusResponse.model_validate(project)


@router.get(
    "/{project_id}/stream",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
    },
)
async def stream_carousel(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    agent: Annotated[CarouselAgent, Depends(get_carousel_agent)],
) -> StreamingResponse:
    """Stream pipeline progress as Server-Sent Events."""

    async def event_generator() -> AsyncIterator[str]:
        async for event in agent.stream_pipeline(project_id, seed_urls=None):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(event_generator(), media_type=MEDIA_TYPE_STREAM)


@router.post(
    "/{project_id}/resume",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
        503: {"description": "Resume unavailable"},
    },
)
async def resume_carousel(
    project_id: UUID,
    user: Annotated[User, Depends(require_editor_or_admin)],
    agent: Annotated[CarouselAgent, Depends(get_carousel_agent)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselStatusResponse:
    """Resume an interrupted pipeline from its last checkpoint."""
    try:
        agent.start_pipeline(project_id, seed_urls=None)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Resume unavailable: {exc}",
        ) from exc

    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    return CarouselStatusResponse.model_validate(project)


@router.get(
    "/{project_id}/status",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        404: {"description": ERR_NOT_FOUND},
    },
)
async def get_carousel_status(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselStatusResponse:
    """Check carousel generation status."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    return CarouselStatusResponse.model_validate(project)
