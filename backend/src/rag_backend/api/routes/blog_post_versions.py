"""API routes for blog post version history."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.blog_post import (
    BlogPostResponse,
    BlogPostVersionResponse,
)
from rag_backend.infrastructure.database.models import BlogPostModel

router = APIRouter(tags=["blog_post_versions"])


@router.get(
    "/blog-posts/{post_id}/versions",
    response_model=list[BlogPostVersionResponse],
    summary="Get blog post versions",
)
async def get_blog_post_versions(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> list[BlogPostVersionResponse]:
    """Get version history of a blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    return post.version_history if post.version_history else []


@router.post(
    "/blog-posts/{post_id}/restore-version/{version_number}",
    response_model=BlogPostResponse,
    summary="Restore blog post to version",
)
async def restore_blog_post_version(
    post_id: UUID,
    version_number: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Restore a blog post to a previous version."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    versions = post.version_history if post.version_history else []
    version_data: dict | None = None
    for v_data in versions:
        if isinstance(v_data, dict) and v_data.get("version_number") == version_number:
            version_data = v_data
            break

    if not version_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found",
        )

    post.content = version_data.get("snapshot", {})
    post.title = version_data.get("title", post.title)
    post.excerpt = version_data.get("excerpt", post.excerpt)

    max_version = max(
        (v.get("version_number", 0) for v in versions if isinstance(v, dict)),
        default=0,
    )
    new_version_number = max_version + 1
    snapshot = post.content.copy()
    post.version_history.append({
        "id": str(uuid4()),
        "content_id": str(post_id),
        "content_type": "blog_post",
        "version_number": new_version_number,
        "snapshot": snapshot,
        "change_summary": f"Restored from version {version_number}",
        "author_id": current_user.id,
        "created_at": datetime.now(UTC),
    })

    await db.commit()
    await db.refresh(post)
    return post
