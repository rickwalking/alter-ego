"""Lease-fenced run-state persistence of a blog generation (AE-0425, ADR-0025).

The run's metadata writes (heartbeat, final status) are a compare-and-set:
``WHERE id = :post AND generation.lease_id = :mine AND lock_version = :seen``.
A new attempt (retry) and the reaper rotate the lease **and** bump
``lock_version``, so a stale/duplicate task's write affects zero rows and
raises :class:`LeaseLostError`; it can never clobber a newer run. CONTENT
writes do not go through here: they use AE-0424's slot-write path (row lock,
apply onto the latest document, version snapshot), see
``bootstrap/blog_generation_store.py``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

import structlog
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from rag_backend.application.services.blog.blog_image_budget import image_generations
from rag_backend.domain.constants.blog_document import (
    GENERATION_KEY,
    GENERATION_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.blog_generation import (
    GEN_KEY_LEASE_ID,
    GEN_KEY_STATUS,
    LOG_GENERATION_REAPED,
)
from rag_backend.domain.models.blog_generation import (
    GenerationLease,
    GenerationOutcome,
    LeaseLostError,
)
from rag_backend.domain.models.blog_generation_state import (
    finished,
    heartbeat,
    is_stale,
    lease_of,
    reaped,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

logger = structlog.get_logger(__name__)

SessionFactory = async_sessionmaker[AsyncSession]
_CAS_ATTEMPTS = 3


def _now() -> str:
    return datetime.now(UTC).isoformat()


def generation_field(key: str) -> ColumnElement[str]:
    """``ai_generation_metadata.generation.<key>`` as a SQL string expression."""
    column = BlogPostModel.__table__.c.ai_generation_metadata
    return cast(ColumnElement[str], column[GENERATION_KEY, key].as_string())


@dataclass(frozen=True)
class _Row:
    lock_version: int
    metadata: dict[str, object]
    content: dict[str, object]


@dataclass(frozen=True)
class _Mutation:
    """How one fenced write changes the row."""

    values: Callable[[_Row], dict[str, object]]


class SqlBlogGenerationStore:
    """``BlogGenerationStore`` over ``blog_posts`` (one instance per run)."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions
        # Serializes this run's own writes (heartbeat vs content) so one
        # read-modify-write of the metadata never overwrites another.
        self._lock = asyncio.Lock()

    async def heartbeat(self, lease: GenerationLease) -> None:
        """Stamp ``generation.heartbeat_at`` (metadata only)."""
        await self._fenced(
            lease,
            _Mutation(
                lambda row: {"ai_generation_metadata": heartbeat(row.metadata, _now())}
            ),
        )

    async def read_content(self, lease: GenerationLease) -> dict[str, object]:
        """The row's current ``content`` (still fenced on the lease)."""
        row = await self._read_fenced(lease)
        return row.content

    async def images_generated(self, lease: GenerationLease) -> int:
        """Images generated for the post so far (AE-0424's per-post counter)."""
        row = await self._read_fenced(lease)
        return image_generations(row.metadata)

    async def _read_fenced(self, lease: GenerationLease) -> _Row:
        async with self._lock, self._sessions() as session:
            row = await _read(session, lease.post_id)
        if row is None or lease_of(row.metadata) != lease.lease_id:
            raise LeaseLostError(lease.post_id)
        return row

    async def finish(self, lease: GenerationLease, outcome: GenerationOutcome) -> None:
        """Record the final status/errors (metadata only)."""
        await self._fenced(
            lease,
            _Mutation(lambda row: _finish_values(row, outcome)),
        )

    async def _fenced(self, lease: GenerationLease, mutation: _Mutation) -> None:
        async with self._lock:
            for _attempt in range(_CAS_ATTEMPTS):
                if await self._try_once(lease, mutation):
                    return
            raise LeaseLostError(lease.post_id)

    async def _try_once(self, lease: GenerationLease, mutation: _Mutation) -> bool:
        # ``begin()`` commits on exit (rolls back on a raise).
        async with self._sessions.begin() as session:
            row = await _read(session, lease.post_id)
            if row is None or lease_of(row.metadata) != lease.lease_id:
                raise LeaseLostError(lease.post_id)
            values = mutation.values(row)
            written = await _compare_and_set(session, (lease, row), values)
        return written


def _finish_values(row: _Row, outcome: GenerationOutcome) -> dict[str, object]:
    values: dict[str, object] = {
        "ai_generation_metadata": finished(row.metadata, outcome, _now())
    }
    if outcome.title:
        values["title"] = outcome.title
    return values


async def _read(session: AsyncSession, post_id: str) -> _Row | None:
    result = await session.execute(
        select(
            BlogPostModel.lock_version,
            BlogPostModel.ai_generation_metadata,
            BlogPostModel.content,
        ).where(BlogPostModel.id == post_id)
    )
    found = result.one_or_none()
    if found is None:
        return None
    metadata = found[1] if isinstance(found[1], dict) else {}
    content = found[2] if isinstance(found[2], dict) else {}
    return _Row(
        lock_version=int(found[0]), metadata=dict(metadata), content=dict(content)
    )


async def _compare_and_set(
    session: AsyncSession,
    target: tuple[GenerationLease, _Row],
    values: dict[str, object],
) -> bool:
    lease, row = target
    result = await session.execute(
        update(BlogPostModel)
        .where(
            BlogPostModel.id == lease.post_id,
            generation_field(GEN_KEY_LEASE_ID) == lease.lease_id,
            BlogPostModel.lock_version == row.lock_version,
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    return cast(CursorResult[object], result).rowcount == 1


class SqlBlogGenerationReaper:
    """Worker-tick step: ``in_progress`` rows with a stale heartbeat → ``failed``.

    Runs on the existing ``run_workflow_workers`` tick (default every 60 s).
    Partial content is preserved; the lease is revoked so a zombie task of the
    killed run can no longer write; the owner retries (no automatic re-enqueue).
    """

    def __init__(self, stale_seconds: int) -> None:
        self._stale = timedelta(seconds=stale_seconds)

    async def tick(self, db: AsyncSession) -> int:
        """Reap stale runs on the tick's session; returns how many were reaped."""
        cutoff = datetime.now(UTC) - self._stale
        result = await db.execute(
            select(
                BlogPostModel.id,
                BlogPostModel.lock_version,
                BlogPostModel.ai_generation_metadata,
            ).where(generation_field(GEN_KEY_STATUS) == GENERATION_STATUS_IN_PROGRESS)
        )
        reaped_count = 0
        for post_id, lock_version, metadata in result.all():
            if not is_stale(metadata, cutoff):
                continue
            reaped_count += await _reap_one(
                db, (str(post_id), int(lock_version), metadata)
            )
        return reaped_count


async def _reap_one(db: AsyncSession, row: tuple[str, int, object]) -> int:
    post_id, lock_version, metadata = row
    result = await db.execute(
        update(BlogPostModel)
        .where(BlogPostModel.id == post_id, BlogPostModel.lock_version == lock_version)
        .values(
            ai_generation_metadata=reaped(metadata, _now()),
            lock_version=lock_version + 1,
        )
        .execution_options(synchronize_session=False)
    )
    if cast(CursorResult[object], result).rowcount != 1:
        return 0
    logger.warning(LOG_GENERATION_REAPED, post_id=post_id)
    return 1


__all__ = ["SqlBlogGenerationReaper", "SqlBlogGenerationStore", "generation_field"]
