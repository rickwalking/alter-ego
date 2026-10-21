"""The one versioned write path for a blog post's content.

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

from rag_backend.api.dependencies.resource_access import lock_blog_post
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


class VersionedRow(Protocol):
    """A row with an optimistic-lock version."""

    lock_version: int


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
    """One versioned content write of ``post`` by ``user_id``.

    events is built by the route, which already owns the settings and event-publisher
    edge.
    """

    post: BlogPostRow
    if_match: int | None
    values: dict[str, object]
    user_id: str
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


def bump_lock_version(post: VersionedRow) -> None:
    """A status transition is a versioned write: stale editors get a 409.

    Submit / approve / reject / publish / schedule / cancel bump the lock so a
    slot write or save prepared against the pre-transition state cannot land
    without the review reset being decided on the new state.
    """
    post.lock_version = int(post.lock_version or 1) + 1


def _pre_write_snapshot(write: ContentWrite, locked: BlogPostRow) -> VersionSnapshot:
    """The locked row's state BEFORE this write (what a restore brings back)."""
    content = locked.content
    return VersionSnapshot(
        post_id=str(locked.id),
        title=locked.title,
        excerpt=locked.excerpt,
        content=dict(content) if isinstance(content, dict) else {},
        author_id=write.user_id,
        change_summary=write.change_summary,
    )


async def _emit_reset(
    db: AsyncSession, write: ContentWrite, change: tuple[str, str]
) -> None:
    old_status, new_status = change
    await write.events.emit(
        db,
        event_type=EVENT_TYPE_BLOGPOST_STATUS_CHANGED,
        aggregate_id=str(write.post.id),
        aggregate_type=AGGREGATE_TYPE_BLOG_POST,
        payload={"old_status": old_status, "new_status": new_status},
        metadata={"user_id": write.user_id, "source": EVENT_SOURCE_BLOG_WORKFLOW},
    )


async def write_post_content(db: AsyncSession, write: ContentWrite) -> None:
    """Apply the write under the row lock (no commit; the route owns it).

    The row is re-read ``FOR UPDATE`` first, so the review reset and the
    version snapshot come from the locked state, never from a copy loaded
    before a slow provider call.
    """
    expected = require_if_match(write.if_match)
    locked = await lock_blog_post(db, write.post.id)
    old_status = str(locked.status)
    reset = review_reset_values(old_status, write.values)
    values = {**write.values, **reset}
    try:
        await OptimisticLockService.apply_versioned_update(
            db,
            _VersionedUpdate(
                post_id=str(locked.id),
                expected_version=expected,
                values=values,
                snapshot=_pre_write_snapshot(write, locked),
                prior_history=locked.version_history,
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_VERSION_CONFLICT
        ) from exc
    if reset:
        await _emit_reset(db, write, (old_status, str(reset[KEY_STATUS])))


__all__ = [
    "BlogPostRow",
    "ContentWrite",
    "bump_lock_version",
    "check_optional_if_match",
    "require_if_match",
    "write_post_content",
]
