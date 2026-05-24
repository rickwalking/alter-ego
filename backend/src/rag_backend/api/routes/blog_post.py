"""API routes for blog post management (CRUD)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.blog_post import (
    BlogPostCreate,
    BlogPostListResponse,
    BlogPostResponse,
    BlogPostUpdate,
)
from rag_backend.infrastructure.database.models import BlogPostModel

router = APIRouter(tags=["blog_posts"])


@router.post(
    "/blog-posts",
    response_model=BlogPostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create blog post",
)
async def create_blog_post(
    data: BlogPostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Create a new blog post."""
    post = BlogPostModel.from_entity(data.model_dump())
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.get(
    "/blog-posts",
    response_model=BlogPostListResponse,
    summary="List blog posts",
)
async def list_blog_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    status_filter: str | None = Query(None, alias="status"),
    author_id: str | None = Query(None),
) -> BlogPostListResponse:
    """List all blog posts."""
    query = select(BlogPostModel)

    if status_filter:
        query = query.where(BlogPostModel.status == status_filter)
    if author_id:
        query = query.where(BlogPostModel.author_id == author_id)

    result = await db.execute(query)
    posts = result.scalars().all()
    return BlogPostListResponse(items=list(posts), total=len(posts))


@router.get(
    "/blog-posts/{post_id}",
    response_model=BlogPostResponse,
    summary="Get blog post",
)
async def get_blog_post(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Get a specific blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )
    return post


@router.put(
    "/blog-posts/{post_id}",
    response_model=BlogPostResponse,
    summary="Update blog post",
)
async def update_blog_post(
    post_id: UUID,
    data: BlogPostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Update a blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post)
    return post


@router.delete(
    "/blog-posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete blog post",
)
async def delete_blog_post(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> None:
    """Delete a blog post."""
    post = await db.get(BlogPostModel, str(post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post not found: {post_id}",
        )

    await db.delete(post)
    await db.commit()
