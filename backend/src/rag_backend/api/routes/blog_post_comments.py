"""API routes for blog post editorial comments."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.blog_post import (
    EditorialCommentCreate,
    EditorialCommentListResponse,
    EditorialCommentResponse,
)
from rag_backend.domain.constants.blog_post import EditorialCommentStatus
from rag_backend.infrastructure.database.models import BlogPostModel
from rag_backend.infrastructure.database.models.source_comment import EditorialCommentModel

router = APIRouter(tags=["blog_post_comments"])


@router.post(
    "/blog-posts/{post_id}/comments",
    response_model=EditorialCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add editorial comment",
)
async def add_blog_post_comment(
    post_id: UUID,
    data: EditorialCommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    author_id: str = Query(...),
) -> EditorialCommentResponse:
    """Add an editorial comment to a blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    comment = EditorialCommentModel(
        content_id=str(post_id),
        content_type=data.content_type,
        author_id=author_id,
        text=data.text,
        position=data.position,
        ai_suggestion=data.ai_suggestion,
        status=EditorialCommentStatus.OPEN,
    )

    post.editor_comments = post.editor_comments or []
    post.editor_comments.append(str(comment.id))

    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.get(
    "/blog-posts/{post_id}/comments",
    response_model=EditorialCommentListResponse,
    summary="Get editorial comments",
)
async def get_blog_post_comments(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> EditorialCommentListResponse:
    """Get all editorial comments for a blog post."""
    query = select(EditorialCommentModel).where(
        EditorialCommentModel.content_id == str(post_id),
    )
    result = await db.execute(query)
    comments = result.scalars().all()
    return EditorialCommentListResponse(items=list(comments), total=len(comments))
