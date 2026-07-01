"""Public, unauthenticated blog-post read API (AE-0297, ADR-0013).

Serves ONLY ``published`` posts through the lean allow-list schema. This
router is **role-blind by construction**: no auth dependency of any kind is
resolved (a dependency-tree test enforces it), every non-published state is a
uniform 404 (no existence leak), reads perform zero DB writes, and responses
are ``Cache-Control: no-store`` until a CDN strategy lands (ADR-0013).
Resolution is **id-only** in v1 (slug deferred — id/slug oracle risk).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.public_blog_post import (
    PublicBlogPostListResponse,
    PublicBlogPostResponse,
    to_public_detail,
    to_public_summary,
)
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_PUBLIC_BLOG_READ
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

router = APIRouter(tags=["public_blog_posts"])

ERR_PUBLIC_BLOG_POST_NOT_FOUND = "blog_post_not_found"
CACHE_CONTROL_HEADER = "Cache-Control"
CACHE_CONTROL_NO_STORE = "no-store"

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


def _set_no_store(response: Response) -> None:
    response.headers[CACHE_CONTROL_HEADER] = CACHE_CONTROL_NO_STORE


@router.get(
    "/public/blog-posts",
    response_model=PublicBlogPostListResponse,
    summary="List published blog posts (public)",
)
@limiter.limit(RATE_LIMIT_PUBLIC_BLOG_READ)
async def list_public_blog_posts(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT)] = _DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PublicBlogPostListResponse:
    """Published-only listing; any client status filter is ignored."""
    _set_no_store(response)
    published = BlogPostModel.status == BlogPostStatus.PUBLISHED.value
    total = (
        await db.execute(select(func.count()).select_from(BlogPostModel).where(published))
    ).scalar_one()
    rows = (
        (
            await db.execute(
                select(BlogPostModel)
                .where(published)
                .order_by(BlogPostModel.published_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return PublicBlogPostListResponse(
        items=[to_public_summary(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/public/blog-posts/{post_id}",
    response_model=PublicBlogPostResponse,
    summary="Get a published blog post (public)",
)
@limiter.limit(RATE_LIMIT_PUBLIC_BLOG_READ)
async def get_public_blog_post(
    request: Request,
    response: Response,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicBlogPostResponse:
    """Uniform 404 for missing AND non-published posts (no existence leak)."""
    _set_no_store(response)
    row = (
        await db.execute(
            select(BlogPostModel).where(BlogPostModel.id == str(post_id))
        )
    ).scalar_one_or_none()
    if row is None or row.status != BlogPostStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_PUBLIC_BLOG_POST_NOT_FOUND,
        )
    return to_public_detail(row)
