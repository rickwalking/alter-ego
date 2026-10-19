"""Bulk hide for published carousel-origin blog posts (AE-0422, AC6).

Under ADR-0025 carousel-origin posts are always drafts, created on demand. The
legacy pipeline, however, published one post per carousel save, so production
holds many published ``origin='carousel'`` rows whose body is a mutated slide
dump. AE-0427 owns creating the real replacement posts; this service is the
one-shot operator action that removes the bad ones from the public surface.

Selection is deliberately **not** based on body length or heuristics: *every*
published carousel-origin post is a legacy artifact and is hidden, regardless of
how healthy it looks (AE-0422 AC6). The transition mirrors the workflow
``unpublish`` field write (status → draft, publish stamps cleared) and adds the
``ai_generation_metadata.hidden_bad_post`` marker so the write is auditable and
idempotent — a second run selects nothing.

Layer note: this lives in ``infrastructure/database`` (next to
``workflow_timeout_repository``) because it writes ``BlogPostModel`` directly and
reuses :class:`WorkflowEventService`; that keeps the operator path free of a new
``application -> infrastructure`` edge (the generated AE-0082 baseline is
unchanged).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, cast

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_BLOG_POST,
    EVENT_SOURCE_BLOG_WORKFLOW,
    EVENT_TYPE_BLOGPOST_STATUS_CHANGED,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

HIDDEN_BAD_POST_KEY = "hidden_bad_post"
DEFAULT_HIDE_REASON = "legacy carousel-origin post (AE-0422 AC6)"
DEFAULT_HIDE_ACTOR = "system:ae-0422-hide"


class _HidablePost(Protocol):
    """The instance-shaped view of ``BlogPostModel`` this service mutates.

    ``BlogPostModel`` declares several columns with legacy ``Column(...)`` (not
    ``Mapped``), so SQLAlchemy attribute access is typed as ``Column[T]`` rather
    than the runtime instance value. This Protocol (reached via ``cast`` on a
    real row) gives the plain Python types of a loaded instance.
    """

    id: object
    origin: str
    status: str
    published_at: datetime | None
    submitted_for_review_at: datetime | None
    lock_version: int
    ai_generation_metadata: dict[str, object]


@dataclass(frozen=True)
class HideRun:
    """Parameters for one hide run (grouped to keep the call signature small)."""

    reason: str = DEFAULT_HIDE_REASON
    now: datetime | None = None
    user_id: str = DEFAULT_HIDE_ACTOR


@dataclass(frozen=True)
class HideReport:
    """Outcome of a hide run (dry-run reports the same ``ids`` with zero writes)."""

    ids: list[str] = field(default_factory=list)
    reason: str = DEFAULT_HIDE_REASON

    @property
    def count(self) -> int:
        return len(self.ids)


def is_hide_target(post: BlogPostModel) -> bool:
    """A post is hidden iff it is carousel-origin **and** currently published."""
    origin = cast("str", post.origin)
    return (
        origin == BlogPostOrigin.CAROUSEL.value
        and post.status == BlogPostStatus.PUBLISHED.value
    )


class BlogPostHideService:
    """Hide published carousel-origin posts; idempotent and auditable."""

    def __init__(self, emitter: WorkflowEventService) -> None:
        self._emitter = emitter

    async def preview(self, db: AsyncSession) -> HideReport:
        """Return the ids that :meth:`hide` would change, without writing."""
        ids = (await db.execute(self._preview_query())).scalars().all()
        return HideReport(ids=list(ids))

    async def hide(self, db: AsyncSession, run: HideRun | None = None) -> HideReport:
        """Hide every published carousel-origin post in one transaction.

        The caller owns the commit (mirrors the workflow routes): the field
        writes, the marker, and the status events are staged here and flushed.
        Re-running is a no-op because selection only matches ``published`` rows.
        """
        run = run or HideRun()
        at = run.now or datetime.now(UTC)
        rows = (await db.execute(self._targets_query())).scalars().all()
        hidden_ids: list[str] = []
        for post in rows:
            row = cast("_HidablePost", post)
            old_status = row.status
            row.status = BlogPostStatus.DRAFT.value
            row.published_at = None
            row.submitted_for_review_at = None
            row.lock_version = (row.lock_version or 0) + 1
            row.ai_generation_metadata = {
                **row.ai_generation_metadata,
                HIDDEN_BAD_POST_KEY: {"at": at.isoformat(), "reason": run.reason},
            }
            await self._emitter.emit(
                db,
                event_type=EVENT_TYPE_BLOGPOST_STATUS_CHANGED,
                aggregate_id=str(row.id),
                aggregate_type=AGGREGATE_TYPE_BLOG_POST,
                payload={"old_status": old_status, "new_status": row.status},
                metadata={
                    "user_id": run.user_id,
                    "source": EVENT_SOURCE_BLOG_WORKFLOW,
                    "reason": run.reason,
                },
            )
            hidden_ids.append(str(row.id))
        await db.flush()
        if hidden_ids:
            # structlog key/value (not %-style args, which raise once the app
            # has configured structlog; found as an order-dependent test failure).
            logger.info("blog_posts_hidden", count=len(hidden_ids), reason=run.reason)
        return HideReport(ids=hidden_ids, reason=run.reason)

    @staticmethod
    def _target_conditions() -> tuple[ColumnElement[bool], ...]:
        return (
            BlogPostModel.origin == BlogPostOrigin.CAROUSEL.value,
            BlogPostModel.status == BlogPostStatus.PUBLISHED.value,
        )

    @classmethod
    def _targets_query(cls) -> Select[tuple[BlogPostModel]]:
        return select(BlogPostModel).where(*cls._target_conditions())

    @classmethod
    def _preview_query(cls) -> Select[tuple[str]]:
        return select(BlogPostModel.id).where(*cls._target_conditions())
