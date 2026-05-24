"""API routes for blog post workflow transitions."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.blog_post import BlogPostResponse
from rag_backend.domain.constants.blog_post import BlogPostStatus, EditorialCommentStatus
from rag_backend.infrastructure.database.models import BlogPostModel

router = APIRouter(tags=["blog_post_workflow"])


@router.post(
    "/blog-posts/{post_id}/submit-review",
    response_model=BlogPostResponse,
    summary="Submit blog post for review",
)
async def submit_blog_post_for_review(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Submit a blog post for review."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    post.status = BlogPostStatus.UNDER_REVIEW
    post.submitted_for_review_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/approve",
    response_model=BlogPostResponse,
    summary="Approve blog post",
)
async def approve_blog_post(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    reviewer_id: str = Query(...),
) -> BlogPostResponse:
    """Approve a blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    post.status = BlogPostStatus.APPROVED
    post.approved_at = datetime.now(UTC)
    post.reviewer_id = reviewer_id

    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/reject",
    response_model=BlogPostResponse,
    summary="Reject blog post",
)
async def reject_blog_post(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    reviewer_id: str = Query(...),
    reason: str = Query(...),
) -> BlogPostResponse:
    """Reject a blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    post.status = BlogPostStatus.DRAFT
    post.submitted_for_review_at = None

    if post.editor_comments is None:
        post.editor_comments = []
    post.editor_comments.append({
        "text": f"Rejected: {reason}",
        "author_id": reviewer_id,
        "status": EditorialCommentStatus.OPEN,
    })

    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/publish",
    response_model=BlogPostResponse,
    summary="Publish blog post",
)
async def publish_blog_post(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Publish a blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    post.status = BlogPostStatus.PUBLISHED
    post.published_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/unpublish",
    response_model=BlogPostResponse,
    summary="Unpublish blog post",
)
async def unpublish_blog_post(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Unpublish a blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    post.status = BlogPostStatus.DRAFT
    post.published_at = None
    post.submitted_for_review_at = None

    await db.commit()
    await db.refresh(post)
    return post
