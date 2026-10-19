"""The one versioned write path for a blog post's content (AE-0424).

PUT, restore-version, the image routes, rewrite-section and the EN translation
all mutate ``blog_posts.content``; every one of them goes through
:func:`write_post_content`, so each:

- requires ``If-Match`` (428 when missing, 409 ``version_conflict`` when stale);
- appends a ``version_history`` snapshot in the same UPDATE (F-13);
- resets an ``under_review``/``approved`` post to ``draft`` and clears its
  schedule (an edit invalidates the approval), emitting the status event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.blog.blog_review_reset import (
    review_reset_values,
)
from rag_backend.application.services.blog.blog_version_history import (
    VersionSnapshot,
)
from rag_backend.application.services.optimistic_lock_service import (
    OptimisticLockService,
    _VersionedUpdate,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.blog_editor import VERSION_SUMMARY_SAVE
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_BLOG_POST,
    EVENT_SOURCE_BLOG_WORKFLOW,
    EVENT_TYPE_BLOGPOST_STATUS_CHANGED,
)
from rag_backend.domain.constants.workflow_validation import (
    ERR_VERSION_HEADER_REQUIRED,
)

KEY_STATUS = "status"


class BlogPostRow(Protocol):
    """The loaded ``blog_posts`` row fields a content write reads."""

    id: str
    status: str
    title: str
    excerpt: str | None
    content: object
    version_history: object


@dataclass(frozen=True)
class ContentWrite:
    """One versioned content write of ``post`` by ``user_id``."""

    post: BlogPostRow
    if_match: int | None
    values: dict[str, object]
    user_id: str
    # Built by the route (it already owns the settings/event-publisher edge).
    events: WorkflowEventService
    change_summary: str = VERSION_SUMMARY_SAVE


def require_if_match(if_match: int | None) -> int:
    """428 unless the client sent the ``If-Match`` lock version."""
    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail=ERR_VERSION_HEADER_REQUIRED,
        )
    return if_match


async def check_optional_if_match(current: int, if_match: int | None) -> None:
    """409 when an ``If-Match`` was sent and is stale (status-only writes)."""
    try:
        await OptimisticLockService.check_version(current, if_match)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_VERSION_CONFLICT
        ) from exc


def _snapshot(write: ContentWrite, values: dict[str, object]) -> VersionSnapshot:
    post = write.post
    content = values.get("content", post.content)
    excerpt = values.get("excerpt", post.excerpt)
    return VersionSnapshot(
        post_id=str(post.id),
        title=str(values.get("title", post.title)),
        excerpt=excerpt if isinstance(excerpt, str) else None,
        content=content if isinstance(content, dict) else {},
        author_id=write.user_id,
        change_summary=write.change_summary,
    )


async def _emit_reset(db: AsyncSession, write: ContentWrite, new_status: str) -> None:
    await write.events.emit(
        db,
        event_type=EVENT_TYPE_BLOGPOST_STATUS_CHANGED,
        aggregate_id=str(write.post.id),
        aggregate_type=AGGREGATE_TYPE_BLOG_POST,
        payload={"old_status": write.post.status, "new_status": new_status},
        metadata={"user_id": write.user_id, "source": EVENT_SOURCE_BLOG_WORKFLOW},
    )


async def write_post_content(db: AsyncSession, write: ContentWrite) -> None:
    """Apply the write under the lock (no commit; the route owns it)."""
    expected = require_if_match(write.if_match)
    reset = review_reset_values(write.post.status, write.values)
    values = {**write.values, **reset}
    try:
        await OptimisticLockService.apply_versioned_update(
            db,
            _VersionedUpdate(
                post_id=str(write.post.id),
                expected_version=expected,
                values=values,
                snapshot=_snapshot(write, values),
                prior_history=write.post.version_history,
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_VERSION_CONFLICT
        ) from exc
    if reset:
        await _emit_reset(db, write, str(reset[KEY_STATUS]))


__all__ = [
    "BlogPostRow",
    "ContentWrite",
    "check_optional_if_match",
    "require_if_match",
    "write_post_content",
]
