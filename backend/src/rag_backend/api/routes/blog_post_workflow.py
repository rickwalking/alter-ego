"""API routes for blog post workflow transitions (Phase 3 WF-003)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import (
    assert_blog_post_reviewer_or_admin,
    assert_blog_post_status,
    get_blog_post_by_id,
    get_blog_post_for_user,
    validate_reviewer_user,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.blog_post import BlogPostResponse
from rag_backend.api.schemas.calendar import SchedulePublishRequest
from rag_backend.application.services.ai_disclosure_service import AiDisclosureService
from rag_backend.application.services.notification_service import (
    NotificationService,
    _WorkflowUpdateParams,
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
    MAX_REJECT_REASON_LENGTH,
    MIN_SCHEDULE_LEAD_SECONDS,
    NOTIFICATION_TITLE_CHANGES_REQUESTED,
    WORKFLOW_REJECT_COMMENT_PREFIX,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.events.factory import get_event_publisher

router = APIRouter(tags=["blog_post_workflow"])


def _event_service() -> WorkflowEventService:
    settings = get_settings()
    return WorkflowEventService(get_event_publisher(settings.redis_url or None))


def _scheduler() -> ScheduledPublishService:
    return ScheduledPublishService(
        get_session_maker(),
        _event_service(),
        NotificationService(),
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

    post.status = BlogPostStatus.PUBLISHED.value
    post.published_at = datetime.now(UTC)
    post.scheduled_publish_at = None

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
    await _scheduler().schedule_post(db, post, scheduled_at)
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
) -> BlogPostResponse:
    """Unpublish a blog post."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    assert_blog_post_status(post, BlogPostStatus.PUBLISHED)
    old_status = post.status

    post.status = BlogPostStatus.DRAFT.value
    post.published_at = None
    post.submitted_for_review_at = None

    await _emit_status_change(
        db, str(post.id), old_status, post.status, current_user.id
    )
    await db.commit()
    await db.refresh(post)
    return post
