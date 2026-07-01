"""API routes for blog post workflow transitions (Phase 3 WF-003)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.publishing import (
    PublishingComposition,
    build_publishing_module,
)
from rag_backend.api.dependencies.resource_access import (
    assert_blog_post_reviewer_or_admin,
    assert_blog_post_status,
    get_blog_post_by_id,
    get_blog_post_for_user,
    validate_reviewer_user,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.deps import get_carousel_repo
from rag_backend.api.schemas.blog_post import BlogPostResponse
from rag_backend.api.schemas.calendar import SchedulePublishRequest
from rag_backend.application.services.ai_disclosure_service import AiDisclosureService
from rag_backend.application.services.notification_service import (
    NotificationService,
    _WorkflowUpdateParams,
)
from rag_backend.application.services.optimistic_lock_service import (
    OptimisticLockService,
)
from rag_backend.application.services.scheduled_publish_service import (
    ScheduledPublishService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.ai_disclosure import (
    AI_DISCLOSURE_NONE,
    ERR_DISCLOSURE_REQUIRED,
)
from rag_backend.domain.constants.blog_post import (
    BlogPostStatus,
    EditorialCommentStatus,
)
from rag_backend.domain.constants.notifications import NOTIFICATION_TYPE_PHASE_REJECTED
from rag_backend.domain.constants.optimistic_locking import (
    ERR_VERSION_CONFLICT,
    HTTP_HEADER_IF_MATCH,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_BLOG_POST,
    EVENT_SOURCE_BLOG_WORKFLOW,
    EVENT_TYPE_BLOGPOST_STATUS_CHANGED,
)
from rag_backend.domain.constants.workflow_validation import (
    CONTENT_TYPE_BLOG_POST,
    ERR_SCHEDULE_IN_PAST,
    ERR_SELF_REVIEW,
    ERR_VERSION_HEADER_REQUIRED,
    MAX_REJECT_REASON_LENGTH,
    MIN_SCHEDULE_LEAD_SECONDS,
    NOTIFICATION_TITLE_CHANGES_REQUESTED,
    WORKFLOW_REJECT_COMMENT_PREFIX,
)
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.modules.publishing import PublishingModule

router = APIRouter(tags=["blog_post_workflow"])


def _event_service() -> WorkflowEventService:
    settings = get_settings()
    return WorkflowEventService(get_event_publisher(settings.redis_url or None))


def _scheduler() -> ScheduledPublishService:
    """Build the scheduled-publish service exactly as the legacy route did.

    Byte-identical to the pre-AE-0128 ``_scheduler`` helper — the same session
    maker, the same Redis-backed workflow-event service, and the same notification
    service — so the schedule write + the due-post sweep are unchanged.
    """
    return ScheduledPublishService(
        get_session_maker(),
        _event_service(),
        NotificationService(),
    )


def get_publishing_module_for_blog(
    db: Annotated[AsyncSession, Depends(get_db)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> PublishingModule:
    """Build the request-scoped publishing facade for the blog workflow edge.

    Binds the facade to the SAME ``get_db`` session the blog publish/unpublish/
    schedule routes already use, so the visibility/schedule writes flush into that
    transaction and the route owns the single commit (unchanged). The carousel
    repository is resolved through the existing ``get_carousel_repo`` dependency (an
    api→api edge, mirroring ``crud.py``; no service-locator), and the scheduler is
    built exactly as the legacy route did — keeping the shared
    ``api/dependencies/publishing`` edge free of any new ``api -> infrastructure``
    import (the grandfathered baseline only).
    """
    return build_publishing_module(
        PublishingComposition(
            session=db,
            carousel_repository=repo,
            scheduler=_scheduler(),
        ),
    )


async def _emit_status_change(
    db: AsyncSession,
    post_id: str,
    old_status: str,
    new_status: str,
    user_id: str,
) -> None:
    await _event_service().emit(
        db,
        event_type=EVENT_TYPE_BLOGPOST_STATUS_CHANGED,
        aggregate_id=post_id,
        aggregate_type=AGGREGATE_TYPE_BLOG_POST,
        payload={"old_status": old_status, "new_status": new_status},
        metadata={"user_id": user_id, "source": EVENT_SOURCE_BLOG_WORKFLOW},
    )


@router.post(
    "/blog-posts/{post_id}/submit-review",
    response_model=BlogPostResponse,
    summary="Submit blog post for review",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def submit_blog_post_for_review(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    reviewer_id: str = Query(...),
) -> BlogPostResponse:
    """Submit a blog post for review."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    assert_blog_post_status(post, BlogPostStatus.DRAFT)
    old_status = post.status

    await validate_reviewer_user(db, reviewer_id)
    if post.author_id and reviewer_id == post.author_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_SELF_REVIEW,
        )

    post.status = BlogPostStatus.UNDER_REVIEW.value
    post.submitted_for_review_at = datetime.now(UTC)
    post.reviewer_id = reviewer_id

    await _emit_status_change(
        db, str(post.id), old_status, post.status, current_user.id
    )
    if reviewer_id != current_user.id:
        await NotificationService().create_review_request(
            db,
            user_id=reviewer_id,
            content_id=str(post.id),
            content_type=CONTENT_TYPE_BLOG_POST,
            title=post.title,
        )

    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/approve",
    response_model=BlogPostResponse,
    summary="Approve blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def approve_blog_post(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostResponse:
    """Approve a blog post (assigned reviewer or admin only)."""
    post = await get_blog_post_by_id(db, post_id)
    assert_blog_post_status(post, BlogPostStatus.UNDER_REVIEW)
    assert_blog_post_reviewer_or_admin(post, current_user)
    old_status = post.status

    post.status = BlogPostStatus.APPROVED.value
    post.approved_at = datetime.now(UTC)

    await _emit_status_change(
        db, str(post.id), old_status, post.status, current_user.id
    )
    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/reject",
    response_model=BlogPostResponse,
    summary="Reject blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def reject_blog_post(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    reason: str = Query(..., max_length=MAX_REJECT_REASON_LENGTH),
) -> BlogPostResponse:
    """Reject a blog post (assigned reviewer or admin only)."""
    post = await get_blog_post_by_id(db, post_id)
    assert_blog_post_status(post, BlogPostStatus.UNDER_REVIEW)
    assert_blog_post_reviewer_or_admin(post, current_user)
    old_status = post.status

    post.status = BlogPostStatus.DRAFT.value
    post.submitted_for_review_at = None

    if post.editor_comments is None:
        post.editor_comments = []
    post.editor_comments.append({
        "text": WORKFLOW_REJECT_COMMENT_PREFIX.format(reason=reason),
        "author_id": current_user.id,
        "status": EditorialCommentStatus.OPEN.value,
    })

    await _emit_status_change(
        db, str(post.id), old_status, post.status, current_user.id
    )
    if post.author_id:
        await NotificationService().create_workflow_update(
            db,
            _WorkflowUpdateParams(
                user_id=post.author_id,
                notification_type=NOTIFICATION_TYPE_PHASE_REJECTED,
                title=NOTIFICATION_TITLE_CHANGES_REQUESTED.format(title=post.title),
                body=reason,
                content_id=str(post.id),
                content_type=CONTENT_TYPE_BLOG_POST,
            ),
        )

    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/publish",
    response_model=BlogPostResponse,
    summary="Publish blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def publish_blog_post(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    publishing: Annotated[PublishingModule, Depends(get_publishing_module_for_blog)],
) -> BlogPostResponse:
    """Publish an approved blog post (author or admin only)."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    assert_blog_post_status(post, BlogPostStatus.APPROVED)

    disclosure = AiDisclosureService()
    metadata = (
        post.ai_generation_metadata
        if isinstance(post.ai_generation_metadata, dict)
        else {}
    )
    label = str(post.ai_disclosure_label or disclosure.compute_label(metadata))
    if disclosure.requires_disclosure(label) and label == AI_DISCLOSURE_NONE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_DISCLOSURE_REQUIRED,
        )

    old_status = post.status

    await publishing.service.publish_blog(post)

    await _emit_status_change(
        db, str(post.id), old_status, post.status, current_user.id
    )
    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/schedule",
    response_model=BlogPostResponse,
    summary="Schedule blog post for future publication",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def schedule_blog_post(
    request: Request,
    post_id: UUID,
    body: SchedulePublishRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    publishing: Annotated[PublishingModule, Depends(get_publishing_module_for_blog)],
) -> BlogPostResponse:
    """Schedule an approved post for future publication (SCHED-001, UI-024)."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    assert_blog_post_status(post, BlogPostStatus.APPROVED)
    min_schedule = datetime.now(UTC) + timedelta(seconds=MIN_SCHEDULE_LEAD_SECONDS)
    scheduled_at = body.scheduled_publish_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)
    if scheduled_at < min_schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_SCHEDULE_IN_PAST,
        )
    await publishing.service.schedule_blog(post, scheduled_at)
    await db.commit()
    await db.refresh(post)
    return post


@router.post(
    "/blog-posts/{post_id}/unpublish",
    response_model=BlogPostResponse,
    summary="Unpublish blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def unpublish_blog_post(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    publishing: Annotated[PublishingModule, Depends(get_publishing_module_for_blog)],
    if_match: Annotated[int | None, Header(alias=HTTP_HEADER_IF_MATCH)] = None,
) -> BlogPostResponse:
    """Unpublish a blog post (optimistic-locked visibility flip; AE-0296)."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail=ERR_VERSION_HEADER_REQUIRED,
        )
    assert_blog_post_status(post, BlogPostStatus.PUBLISHED)
    try:
        await OptimisticLockService.check_version(post.lock_version, if_match)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_VERSION_CONFLICT,
        ) from exc
    old_status = post.status

    await publishing.service.unpublish_blog(post)
    # A visibility flip is a versioned write like any other: bump the version
    # so a concurrent editor's stale If-Match is rejected instead of clobbered.
    post.lock_version = if_match + 1

    await _emit_status_change(
        db, str(post.id), old_status, post.status, current_user.id
    )
    await db.commit()
    await db.refresh(post)
    return post
