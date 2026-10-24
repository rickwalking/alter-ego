"""Anti-corruption layer: legacy carousel/blog persistence ↔ publishing.

This module is the **single** seam between the publishing bounded context and the
legacy carousel + blog persistence. It is the **only** file under
``rag_backend.modules.publishing`` that imports the carousel/blog ORM for the
release / visibility / schedule writes; the publishing application and domain
layers stay free of it (the layering is enforced by check-integrity + the import
contract). Everything it writes is byte-identical to the legacy
scattered route/service writes — only the *ownership* and the *commit boundary*
are consolidated here.

It backs three publishing domain ports:

* :class:`CarouselReleasePort` — the carousel ``is_public`` public-release write
  (``crud.py:publish_carousel``). The owner writes ONLY ``is_public=True`` /
  ``current_phase=published`` in one targeted UPDATE guarded by the row's
  ``lock_version`` (compare-and-set), then commits ONCE through the platform Unit
  of Work. It never saves the whole carousel loaded earlier, so a caption or copy
  edit committed in between is kept.
* :class:`BlogVisibilityPort` — the standalone blog publish/unpublish status
  writes (``blog_post_workflow.py``). Flush only; the route owns the
  status-change event emission and the single commit (unchanged).
* :class:`BlogSchedulePort` — the standalone blog schedule write + the
  scheduled-publish sweep. ``schedule_publish`` delegates UNCHANGED to the
  existing :class:`ScheduledPublishService.schedule_post` (same
  ``scheduled_publish_at`` write + scheduled event, flush only; the route
  commits); ``process_due_posts`` delegates UNCHANGED to the same service's sweep.

Behavior-preserving: no write here changes a status value, a timestamp,
a visibility flag, the event payloads, or the commit count relative to the legacy
paths; the ``is_public`` semantics + the approval gate (which stays at the route)
are untouched. The carousel ORM uses the legacy ``Column(...)`` declaration style,
so its instance attributes type as ``Column[T]`` under mypy; the carousel release
write reuses the model's plain attribute assignment exactly as the legacy route
did (no ``Mapped[...]`` migration is in scope and none is needed — the values are
identical).

A release or visibility write handed a non-canonical object raises a programmer-error
sentinel (a wiring or type bug, never a request path), mirroring the editorial ACL's
defensive typing seam so the domain ports can stay ORM-free.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.scheduled_publish_service import (
    ScheduledPublishService,
)
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.carousel_workflow import PHASE_PUBLISHED
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.publishing.domain.ports import CarouselRepository
from rag_backend.platform.database import SqlAlchemyUnitOfWork

_ERR_NOT_CAROUSEL = "release_public expected a CarouselProject entity"
_ERR_NOT_BLOG_POST = "blog visibility/schedule write expected a BlogPostModel row"
_RELEASE_ATTEMPTS = 3
_ERR_NO_SCHEDULER = "blog schedule write invoked without a scheduled-publish service"


class LegacyPublishingAcl:
    """Translate legacy carousel/blog persistence to/from publishing writes.

    Binds the request-scoped session (the single carousel/blog ORM seam) and the
    carousel repository the release port is wired with. Wraps the
    same session in the platform Unit of Work so the owner is also the single
    committer for the carousel release write it stages (the blog visibility/schedule
    writes flush only; their route owns the commit, unchanged).
    """

    def __init__(
        self,
        session: AsyncSession,
        carousel_repository: CarouselRepository,
        scheduler: ScheduledPublishService | None = None,
    ) -> None:
        self._session = session
        self._carousel_repository = carousel_repository
        self._scheduler = scheduler
        self._uow = SqlAlchemyUnitOfWork(session)

    async def release_public(self, project: object, project_id: str) -> object:
        """Mark the carousel publicly released; return the released entity.

        Reads the row's ``lock_version`` and runs ``UPDATE ... SET is_public,
        current_phase WHERE id AND lock_version = seen``, then commits ONCE via
        the UoW. A concurrent writer that bumped the version in between makes the
        UPDATE match no row; the release (which writes only those two columns)
        re-reads and tries again, and raises ``version_conflict`` after
        ``_RELEASE_ATTEMPTS``. No other column is written, so a caption edit
        landing after the route loaded ``project`` is never overwritten. A
        missing row writes and commits nothing.
        """
        if not isinstance(project, CarouselProject):
            raise TypeError(_ERR_NOT_CAROUSEL)
        for _attempt in range(_RELEASE_ATTEMPTS):
            written = await self._release_row(project_id)
            if written is None:
                return project
            if written:
                await self._uow.commit()
                project.is_public = True
                project.current_phase = PHASE_PUBLISHED
                return project
        raise ValueError(ERR_VERSION_CONFLICT)

    async def _release_row(self, project_id: str) -> bool | None:
        """One compare-and-set release; None when the carousel row is missing."""
        seen = await self._session.scalar(
            select(CarouselProjectModel.lock_version).where(
                CarouselProjectModel.id == project_id
            )
        )
        if seen is None:
            return None
        result = await self._session.execute(
            update(CarouselProjectModel)
            .where(
                CarouselProjectModel.id == project_id,
                CarouselProjectModel.lock_version == seen,
            )
            .values(is_public=True, current_phase=PHASE_PUBLISHED)
        )
        return cast(CursorResult[object], result).rowcount == 1

    @staticmethod
    async def mark_published(post: object) -> None:
        """Set the blog row to PUBLISHED with ``published_at`` now (flush only).

        Byte-identical to the legacy ``publish_blog_post`` field write: status →
        PUBLISHED, ``published_at`` = now (UTC), ``scheduled_publish_at`` cleared.
        The route owns the status-change event emission + the single commit; the
        mutated row is staged in the route's own session (which the route flushes
        + commits), so this owner needs no session of its own for the write.
        """
        row = _as_blog_post(post)
        row.status = BlogPostStatus.PUBLISHED.value
        row.published_at = datetime.now(UTC)
        row.scheduled_publish_at = None

    @staticmethod
    async def mark_unpublished(post: object) -> None:
        """Revert the blog row to DRAFT and clear publish stamps (flush only).

        Byte-identical to the legacy ``unpublish_blog_post`` field write: status →
        DRAFT, ``published_at`` cleared, ``submitted_for_review_at`` cleared. The
        route owns the status-change event emission + the single commit.
        """
        row = _as_blog_post(post)
        row.status = BlogPostStatus.DRAFT.value
        row.published_at = None
        row.submitted_for_review_at = None

    async def schedule_publish(self, post: object, scheduled_at: datetime) -> None:
        """Stamp ``scheduled_publish_at`` + emit the scheduled event (flush only).

        Delegates UNCHANGED to :meth:`ScheduledPublishService.schedule_post` over
        the request session, so the ``scheduled_publish_at`` write, the scheduled
        event payload, and the flush-only (route-committed) boundary are identical.
        """
        row = _as_blog_post(post)
        await self._require_scheduler().schedule_post(self._session, row, scheduled_at)

    async def process_due_posts(self) -> int:
        """Publish all posts whose scheduled time has passed; return the count.

        Delegates UNCHANGED to :meth:`ScheduledPublishService.process_due_posts`
        (its own session + commit), so the worker sweep is byte-identical.
        """
        return await self._require_scheduler().process_due_posts()

    def _require_scheduler(self) -> ScheduledPublishService:
        """Return the scheduled-publish service, or raise if it was not wired.

        The carousel publish edge composes the ACL without a scheduler (it never
        schedules); a schedule write without one is a wiring error, surfaced here
        rather than as an ``AttributeError``.
        """
        if self._scheduler is None:
            raise RuntimeError(_ERR_NO_SCHEDULER)
        return self._scheduler


def _as_blog_post(post: object) -> BlogPostModel:
    """Narrow a port ``object`` argument back to the canonical blog ORM row.

    The domain ports pass the blog post as ``object`` so the application/domain
    layers import no ORM; the ACL (the sole ORM seam) narrows it here. A mistyped
    argument is a wiring/programming error and surfaces as a ``TypeError``.
    """
    if not isinstance(post, BlogPostModel):
        raise TypeError(_ERR_NOT_BLOG_POST)
    return post


__all__ = ["LegacyPublishingAcl"]
