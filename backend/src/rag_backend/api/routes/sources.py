"""API routes for content source management."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent
from rag_backend.api.dependencies.carousel_access import (
    CarouselSourceQuery,
    ProjectSourceLookup,
    get_carousel_project_for_user,
    get_project_source_for_user,
    list_carousel_sources_for_user,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.blog_post import (
    ContentSourceCreate,
    ContentSourceListResponse,
    ContentSourceResponse,
)
from rag_backend.api.schemas.knowledge_sources import (
    CAROUSEL_SOURCES_DEFAULT_LIMIT,
    CAROUSEL_SOURCES_MAX_LIMIT,
    CarouselSourceListResponse,
)
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AI_ENDPOINTS
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.models.source_comment import ContentSourceModel

router = APIRouter(tags=["content_sources"])


@router.get(
    "/projects/{project_id}/sources",
    response_model=ContentSourceListResponse,
    summary="List content sources for a project",
)
async def list_sources_for_project(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> ContentSourceListResponse:
    """List all content sources for a project."""
    await get_carousel_project_for_user(db, project_id, current_user)
    query = select(ContentSourceModel).where(
        ContentSourceModel.project_id == str(project_id)
    )
    result = await db.execute(query)
    sources = result.scalars().all()
    return ContentSourceListResponse(items=list(sources), total=len(sources))


@dataclass(frozen=True)
class CarouselSourcePage:
    """The paging and carousel filter of the carousel-sources listing."""

    limit: int
    offset: int
    project_id: UUID | None


def get_carousel_source_page(
    limit: Annotated[
        int, Query(ge=1, le=CAROUSEL_SOURCES_MAX_LIMIT)
    ] = CAROUSEL_SOURCES_DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
    project_id: Annotated[UUID | None, Query()] = None,
) -> CarouselSourcePage:
    """Parse the listing's query parameters."""
    return CarouselSourcePage(limit=limit, offset=offset, project_id=project_id)


@router.get(
    "/knowledge/carousel-sources",
    response_model=CarouselSourceListResponse,
    summary="List the content sources of the caller's carousels",
)
async def list_carousel_sources(
    page: Annotated[CarouselSourcePage, Depends(get_carousel_source_page)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> CarouselSourceListResponse:
    """A page of content sources across the caller's carousels, newest first.

    An admin sees every owner's carousels; ``project_id`` narrows the page to
    one carousel, and ``carousels`` lists each carousel with sources for the
    filter.
    """
    return await list_carousel_sources_for_user(
        db,
        CarouselSourceQuery(
            user=current_user,
            limit=page.limit,
            offset=page.offset,
            project_id=page.project_id,
        ),
    )


@router.post(
    "/projects/{project_id}/sources",
    response_model=ContentSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add content source to project",
)
async def add_source_to_project(
    project_id: UUID,
    data: ContentSourceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> ContentSourceResponse:
    """Add a new content source to a project."""
    await get_carousel_project_for_user(db, project_id, current_user)
    source = ContentSourceModel(
        project_id=str(project_id),
        source_type=data.source_type,
        title=data.title,
        content=data.content,
        tags=data.tags,
        is_primary=data.is_primary,
        created_by=current_user.id,
    )

    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.delete(
    "/projects/{project_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove content source from project",
)
async def remove_source_from_project(
    project_id: UUID,
    source_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> None:
    """Remove a content source from a project."""
    source = await get_project_source_for_user(
        db,
        ProjectSourceLookup(
            project_id=project_id,
            source_id=source_id,
            user=current_user,
        ),
    )
    await db.delete(source)
    await db.commit()


@router.post(
    "/projects/{project_id}/sources/{source_id}/extract",
    response_model=ContentSourceResponse,
    summary="Extract key points from source material",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def extract_source_key_points(
    request: Request,
    project_id: UUID,
    source_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> ContentSourceResponse:
    """Run source synthesis agent and persist extracted key points (AI-006)."""
    source = await get_project_source_for_user(
        db,
        ProjectSourceLookup(
            project_id=project_id,
            source_id=source_id,
            user=current_user,
        ),
    )

    container = get_container()
    agent = SourceSynthesisAgent(llm=container.llm_service().role_models.reasoning)
    try:
        extracted = await agent.extract_key_points(
            title=source.title,
            content=source.content,
            source_type=source.source_type,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None

    key_points = extracted.get("key_points", [])
    if isinstance(key_points, list):
        source.extracted_key_points = [str(point) for point in key_points]
    metadata = dict(source.content_metadata or {})
    summary = extracted.get("summary", "")
    if summary:
        metadata["summary"] = str(summary)
    source.content_metadata = metadata

    await db.commit()
    await db.refresh(source)
    return source
