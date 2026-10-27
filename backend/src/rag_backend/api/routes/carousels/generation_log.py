"""Owner/admin generation history for one carousel workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.carousel_access import get_carousel_project_for_user
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser, UserModel
from rag_backend.api.schemas.carousel_generation_log import (
    CarouselGenerationLogResponse,
    GenerationLogPageQuery,
    generation_log_response,
)
from rag_backend.modules.generation_queue.events_public import (
    GenerationLogQuery,
    InvalidGenerationEventCursorError,
    read_generation_log,
)

router = APIRouter(tags=["carousels-generation-log"])
ERR_INVALID_CURSOR = "invalid_generation_log_cursor"


@dataclass(frozen=True)
class GenerationLogRouteDeps:
    """The request-scoped session, caller and page query."""

    session: AsyncSession
    user: UserModel
    page: GenerationLogPageQuery


def get_generation_log_route_deps(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    page: Annotated[GenerationLogPageQuery, Depends()],
) -> GenerationLogRouteDeps:
    """Resolve the three route inputs within the function-argument budget."""
    return GenerationLogRouteDeps(session=session, user=current_user, page=page)


@router.get(
    "/{project_id}/generation-log",
    response_model=CarouselGenerationLogResponse,
    summary="List one carousel's sanitized generation history",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not the owner or an admin"},
        status.HTTP_404_NOT_FOUND: {"description": "Carousel not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid cursor"},
    },
)
async def list_carousel_generation_log(
    project_id: UUID,
    deps: Annotated[GenerationLogRouteDeps, Depends(get_generation_log_route_deps)],
) -> CarouselGenerationLogResponse:
    """Return a bounded keyset page after the workspace access check."""
    await get_carousel_project_for_user(deps.session, project_id, deps.user)
    try:
        page = await read_generation_log(
            deps.session,
            GenerationLogQuery(
                project_id=str(project_id),
                limit=deps.page.limit,
                before=deps.page.before,
            ),
        )
    except InvalidGenerationEventCursorError:
        raise HTTPException(status_code=422, detail=ERR_INVALID_CURSOR) from None
    return generation_log_response(project_id, page)


__all__ = ["router"]
