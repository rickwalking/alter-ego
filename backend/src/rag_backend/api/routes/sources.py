"""API routes for content source management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.source_synthesis_agent import SourceSynthesisAgent
from rag_backend.api.dependencies.carousel_access import (
    ProjectSourceLookup,
    get_carousel_project_for_user,
    get_project_source_for_user,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.blog_post import (
    ContentSourceCreate,
    ContentSourceListResponse,
    ContentSourceResponse,
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
    agent = SourceSynthesisAgent(llm=container.llm_service().chat_model)
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
