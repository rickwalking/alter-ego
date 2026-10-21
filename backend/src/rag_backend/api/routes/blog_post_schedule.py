"""Scheduled publication of an approved blog post (SCHED-001).

``POST /schedule`` stamps a future ``scheduled_publish_at`` on an ``approved``
post (the due-post sweep publishes it); ``DELETE /schedule`` cancels it and the
post stays ``approved``. Both check an ``If-Match`` the editor sends.

Path params are fields of the target dataclass (resolved with Depends()).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.blog_content_write import (
    bump_lock_version,
    check_optional_if_match,
)
from rag_backend.api.dependencies.blog_document import assert_ready_to_publish
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import (
    assert_blog_post_status,
    get_blog_post_for_user,
    lock_blog_post,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.blog_post_workflow import get_publishing_module_for_blog
from rag_backend.api.schemas.blog_post import BlogPostResponse
from rag_backend.api.schemas.calendar import SchedulePublishRequest
from rag_backend.domain.constants.blog_editor import ERR_BLOG_SCHEDULE_NOT_SET
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.optimistic_locking import HTTP_HEADER_IF_MATCH
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.domain.constants.workflow_validation import (
    ERR_SCHEDULE_IN_PAST,
    MIN_SCHEDULE_LEAD_SECONDS,
)
from rag_backend.modules.publishing import PublishingModule

router = APIRouter(tags=["blog_post_workflow"])

IfMatch = Annotated[int | None, Header(alias=HTTP_HEADER_IF_MATCH)]
SCHEDULE_PATH = "/blog-posts/{post_id}/schedule"


@dataclass
class ScheduleTarget:
    """The post, session, caller, publishing facade and optional ``If-Match``."""

    post_id: UUID
    db: Annotated[AsyncSession, Depends(get_db)]
    current_user: EditorUser
    publishing: Annotated[PublishingModule, Depends(get_publishing_module_for_blog)]
    if_match: IfMatch = None


Target = Annotated[ScheduleTarget, Depends()]


def _future_schedule(requested: datetime) -> datetime:
    """The UTC schedule time; 400 when inside the minimum lead time."""
    scheduled_at = requested
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)
    min_schedule = datetime.now(UTC) + timedelta(seconds=MIN_SCHEDULE_LEAD_SECONDS)
    if scheduled_at < min_schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_SCHEDULE_IN_PAST,
        )
    return scheduled_at


@router.post(
    SCHEDULE_PATH,
    response_model=BlogPostResponse,
    summary="Schedule blog post for future publication",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def schedule_blog_post(
    request: Request, body: SchedulePublishRequest, target: Target
) -> BlogPostResponse:
    """Schedule an approved post for future publication (SCHED-001, UI-024).

    The transition runs under the row lock: an overlapping slot write (review reset)
    either commits first and is seen here, or waits for this one.
    """
    post = await get_blog_post_for_user(target.db, target.post_id, target.current_user)
    post = await lock_blog_post(target.db, post.id)
    assert_blog_post_status(post, BlogPostStatus.APPROVED)
    await check_optional_if_match(post.lock_version, target.if_match)
    assert_ready_to_publish(post)
    scheduled_at = _future_schedule(body.scheduled_publish_at)
    await target.publishing.service.schedule_blog(post, scheduled_at)
    bump_lock_version(post)
    await target.db.commit()
    await target.db.refresh(post)
    return post


@router.delete(
    SCHEDULE_PATH,
    response_model=BlogPostResponse,
    summary="Cancel the scheduled publication of a blog post",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def cancel_blog_post_schedule(
    request: Request, target: Target
) -> BlogPostResponse:
    """Clear ``scheduled_publish_at``; the post stays ``approved``.

    The transition runs under the row lock: an overlapping slot write (review reset)
    either commits first and is seen here, or waits for this one.
    """
    post = await get_blog_post_for_user(target.db, target.post_id, target.current_user)
    post = await lock_blog_post(target.db, post.id)
    assert_blog_post_status(post, BlogPostStatus.APPROVED)
    await check_optional_if_match(post.lock_version, target.if_match)
    if post.scheduled_publish_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_BLOG_SCHEDULE_NOT_SET,
        )
    post.scheduled_publish_at = None
    bump_lock_version(post)
    await target.db.commit()
    await target.db.refresh(post)
    return post
