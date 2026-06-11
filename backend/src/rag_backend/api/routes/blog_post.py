"""API routes for blog post management (CRUD)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import (
    get_blog_post_for_read,
    get_blog_post_for_user,
    guard_blog_post_update_fields,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.blog_post import (
    BlogPostCreate,
    BlogPostListResponse,
    BlogPostResponse,
    BlogPostSummaryResponse,
    BlogPostUpdate,
)
from rag_backend.api.schemas.blog_post_list import BlogPostListParams
from rag_backend.application.services.editorial_audit_service import (
    EditorialAuditService,
    _AuditEntry,
)
from rag_backend.application.services.optimistic_lock_service import (
    OptimisticLockService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.blog_ai import ERR_BLOG_POST_NOT_FOUND
from rag_backend.domain.constants.optimistic_locking import (
    ERR_VERSION_CONFLICT,
    HTTP_HEADER_IF_MATCH,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.domain.constants.workflow_validation import (
    ERR_VERSION_HEADER_REQUIRED,
)
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.blog_post_repository import BlogPostRepository
from rag_backend.infrastructure.database.models import BlogPostModel
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.infrastructure.telemetry.opentelemetry import start_span

router = APIRouter(tags=["blog_posts"])


def _user_is_admin(user: EditorUser) -> bool:
    return user.role == UserRole.ADMIN.value


def _audit_service() -> EditorialAuditService:
    settings = get_settings()
    return EditorialAuditService(
        WorkflowEventService(get_event_publisher(settings.redis_url or None))
    )


@router.post(
    "/blog-posts",
    response_model=BlogPostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def create_blog_post(
    request: Request,
    data: BlogPostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Create a new blog post."""
    payload = data.model_dump(exclude={"author_id"})
    post = BlogPostModel.from_entity(payload)
    post.author_id = current_user.id
    db.add(post)
    await db.flush()
    await _audit_service().log_created(
        db,
        entry=_AuditEntry(
            post_id=str(post.id),
            user_id=current_user.id,
            extra=post.title,
        ),
    )
    await db.commit()
    await db.refresh(post)
    return post


@router.get(
    "/blog-posts",
    response_model=BlogPostListResponse,
    summary="List blog posts",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def list_blog_posts(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    params: Annotated[BlogPostListParams, Depends()],
) -> BlogPostListResponse:
    """List blog posts visible to the caller with pagination and search."""
    with start_span("blog_post.list"):
        repo = BlogPostRepository()
        filter_author = (
            params.author_id if _user_is_admin(current_user) else current_user.id
        )

        posts, total = await repo.list_summaries(
            db,
            status_filter=params.status,
            author_id=filter_author,
            search=params.search,
            limit=params.limit,
            offset=params.offset,
        )

        return BlogPostListResponse(
            items=[BlogPostSummaryResponse.model_validate(p) for p in posts],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )


@router.get(
    "/blog-posts/{post_id}",
    response_model=BlogPostResponse,
    summary="Get blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_blog_post(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Get a specific blog post."""
    return await get_blog_post_for_read(db, post_id, current_user)


@router.put(
    "/blog-posts/{post_id}",
    response_model=BlogPostResponse,
    summary="Update blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def update_blog_post(
    request: Request,
    post_id: UUID,
    data: BlogPostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    if_match: Annotated[int | None, Header(alias=HTTP_HEADER_IF_MATCH)] = None,
) -> BlogPostResponse:
    """Update a blog post with optimistic locking (WF-005)."""
    await get_blog_post_for_user(db, post_id, current_user)
    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail=ERR_VERSION_HEADER_REQUIRED,
        )

    update_data = data.model_dump(exclude_unset=True)
    guard_blog_post_update_fields(update_data, is_admin=_user_is_admin(current_user))

    lock_service = OptimisticLockService()
    try:
        await lock_service.apply_versioned_update(
            db,
            post_id=str(post_id),
            expected_version=if_match,
            values=update_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_VERSION_CONFLICT,
        ) from exc

    post = await db.get(BlogPostModel, str(post_id))
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_BLOG_POST_NOT_FOUND.format(post_id=post_id),
        )
    await _audit_service().log_updated(
        db,
        entry=_AuditEntry(
            post_id=str(post_id),
            user_id=current_user.id,
            extra=list(update_data.keys()),
        ),
    )
    await db.commit()
    await db.refresh(post)
    return post


@router.delete(
    "/blog-posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def delete_blog_post(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> None:
    """Delete a blog post."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    await _audit_service().log_deleted(
        db,
        entry=_AuditEntry(
            post_id=str(post_id),
            user_id=current_user.id,
        ),
    )
    await db.delete(post)
    await db.commit()
