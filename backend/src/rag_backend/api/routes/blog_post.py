"""API routes for blog post management (CRUD)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.blog_content_write import (
    ContentWrite,
    require_if_match,
    write_post_content,
)
from rag_backend.api.dependencies.blog_document import (
    display_content,
    prepare_create_payload,
    prepare_update_values,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.publishing import (
    PublishingComposition,
    build_publishing_module,
)
from rag_backend.api.dependencies.resource_access import (
    get_blog_post_for_read,
    get_blog_post_for_user,
    guard_blog_post_update_fields,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.deps import get_carousel_repo
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
from rag_backend.domain.constants.blog_post import (
    BLOG_POST_HARD_DELETABLE_ORIGINS,
    ERR_BLOG_POST_SLUG_CONFLICT,
    ERR_CAROUSEL_ORIGIN_DELETE_BLOCKED,
    BlogPostOrigin,
)
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
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.infrastructure.telemetry.opentelemetry import start_span
from rag_backend.modules.publishing import (
    BlogListQuery,
    CarouselRepository,
    PublishingModule,
)

router = APIRouter(tags=["blog_posts"])


def get_publishing_module_for_blog(
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishingModule:
    """Build the request-scoped publishing facade for the blog-CRUD edge (AE-0131).

    Binds the read/blog-CRUD ports to the SAME ``get_db`` session the blog routes
    already use (so the staged row, the audit/lock writes, and the single commit
    share one transaction). The carousel repository is resolved via the
    grandfathered ``get_carousel_repo`` edge so this route adds no new
    ``api -> infrastructure`` import; the read ACL (the sole blog ORM seam) backs
    ``new_post``/``get_post``/``list_summaries``.
    """
    return build_publishing_module(
        PublishingComposition(session=db, carousel_repository=repo, with_read=True),
    )


def _user_is_admin(user: EditorUser) -> bool:
    return user.role == UserRole.ADMIN.value


def _event_service() -> WorkflowEventService:
    settings = get_settings()
    return WorkflowEventService(get_event_publisher(settings.redis_url or None))


def _audit_service() -> EditorialAuditService:
    return EditorialAuditService(_event_service())


async def _stage_new_post(db: AsyncSession, post: object) -> None:
    """Flush the new row; a unique-slug clash becomes a clear 409 (AE-0411)."""
    db.add(post)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_BLOG_POST_SLUG_CONFLICT,
        ) from exc


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
    publishing: Annotated[PublishingModule, Depends(get_publishing_module_for_blog)],
) -> BlogPostResponse:
    """Create a new blog post."""
    payload = data.model_dump(exclude={"author_id"})
    prepare_create_payload(payload)
    post = publishing.service.new_blog_post(payload)
    post.author_id = current_user.id
    await _stage_new_post(db, post)
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


def _summary(post: object, public_ids: frozenset[str]) -> BlogPostSummaryResponse:
    """Serialize a list row plus whether it is publicly readable now (AE-0411)."""
    summary = BlogPostSummaryResponse.model_validate(post)
    return summary.model_copy(update={"is_public": str(summary.id) in public_ids})


@router.get(
    "/blog-posts",
    response_model=BlogPostListResponse,
    summary="List blog posts",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def list_blog_posts(
    request: Request,
    current_user: EditorUser,
    params: Annotated[BlogPostListParams, Depends()],
    publishing: Annotated[PublishingModule, Depends(get_publishing_module_for_blog)],
) -> BlogPostListResponse:
    """List blog posts visible to the caller with pagination and search."""
    with start_span("blog_post.list"):
        filter_author = (
            params.author_id if _user_is_admin(current_user) else current_user.id
        )

        posts, total = await publishing.service.list_blog_summaries(
            BlogListQuery(
                status_filter=params.status,
                author_id=filter_author,
                search=params.search,
                limit=params.limit,
                offset=params.offset,
            ),
        )

        public_ids = await publishing.service.public_blog_post_ids([
            str(p.id) for p in posts
        ])
        return BlogPostListResponse(
            items=[_summary(p, public_ids) for p in posts],
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
    """Get a specific blog post (content always as a ``blog.v2`` document)."""
    post = await get_blog_post_for_read(db, post_id, current_user)
    response = BlogPostResponse.model_validate(post)
    content = display_content(post.content, str(post.id))
    return response.model_copy(update={"content": content})


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
    publishing: Annotated[PublishingModule, Depends(get_publishing_module_for_blog)],
    if_match: Annotated[int | None, Header(alias=HTTP_HEADER_IF_MATCH)] = None,
) -> BlogPostResponse:
    """Update a blog post with optimistic locking (WF-005)."""
    existing = await get_blog_post_for_user(db, post_id, current_user)
    require_if_match(if_match)

    update_data = data.model_dump(exclude_unset=True)
    guard_blog_post_update_fields(update_data, is_admin=_user_is_admin(current_user))
    prepare_update_values(update_data, existing.ai_generation_metadata)

    # AE-0424: versioned write + version snapshot + approval reset in one txn.
    await write_post_content(
        db,
        ContentWrite(
            post=existing,
            if_match=if_match,
            values=update_data,
            user_id=current_user.id,
            events=_event_service(),
        ),
    )

    post = await publishing.service.get_blog_post(str(post_id))
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


def _guard_hard_delete(post: object) -> None:
    """Block hard delete of rows that back a live public projection (AE-0296).

    A ``carousel``-origin row still linked to its project is the source of the
    public ``GET /carousels/{id}/blog`` read (ADR-0011); deleting it would 404
    that surface. Erasure path: delete the parent carousel project (the row is
    then detached/flipped to draft and becomes hard-deletable).
    """
    origin = BlogPostOrigin(getattr(post, "origin", BlogPostOrigin.STANDALONE.value))
    if origin in BLOG_POST_HARD_DELETABLE_ORIGINS:
        return
    if getattr(post, "project_id", None) is None:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ERR_CAROUSEL_ORIGIN_DELETE_BLOCKED,
    )


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
    if_match: Annotated[int | None, Header(alias=HTTP_HEADER_IF_MATCH)] = None,
) -> None:
    """Delete a blog post (optimistic-locked, origin-guarded; AE-0296)."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail=ERR_VERSION_HEADER_REQUIRED,
        )
    _guard_hard_delete(post)
    try:
        await OptimisticLockService.check_version(post.lock_version, if_match)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_VERSION_CONFLICT,
        ) from exc
    await _audit_service().log_deleted(
        db,
        entry=_AuditEntry(
            post_id=str(post_id),
            user_id=current_user.id,
        ),
    )
    await db.delete(post)
    await db.commit()
