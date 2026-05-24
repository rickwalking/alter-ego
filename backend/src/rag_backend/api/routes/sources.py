"""API routes for content source management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.blog_post import (
    ContentSourceCreate,
    ContentSourceListResponse,
    ContentSourceResponse,
)
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
    query = select(ContentSourceModel).where(ContentSourceModel.project_id == str(project_id))
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
    source = ContentSourceModel(
        project_id=str(project_id),
        source_type=data.source_type,
        title=data.title,
        content=data.content,
        tags=data.tags,
        is_primary=data.is_primary,
        created_by=data.created_by or current_user.id,
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
    query = select(ContentSourceModel).where(
        ContentSourceModel.id == str(source_id),
        ContentSourceModel.project_id == str(project_id),
    )
    result = await db.execute(query)
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source not found: {source_id}",
        )

    await db.delete(source)
    await db.commit()
