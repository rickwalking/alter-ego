"""Lease-fenced persistence of a blog generation run (AE-0425, ADR-0025).

Every write of a run is a compare-and-set on the row:
``WHERE id = :post AND generation.lease_id = :mine AND lock_version = :seen``.
A new attempt (retry) and the reaper rotate the lease **and** bump
``lock_version``, so a stale/duplicate task's write affects zero rows and
raises :class:`LeaseLostError`; it can never clobber a newer run. Content
writes also bump ``lock_version`` and fail with
:class:`GenerationConflictError` if the owner saved the row meanwhile.
Heartbeats and the final status write only touch ``ai_generation_metadata``.
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
    ContentMerge,
    ContentWrite,
    GenerationConflictError,
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
    with_voice_score,
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
    bump: bool = False
    expect_version: bool = False


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

    async def write_content(self, lease: GenerationLease, write: ContentWrite) -> None:
        """Store the document + cover projection + voice-score mirror.

        Refuses to overwrite an owner save (``GenerationConflictError``).
        """
        await self._fenced(
            lease,
            _Mutation(
                lambda row: _content_values(row, write), bump=True, expect_version=True
            ),
        )

    async def read_content(self, lease: GenerationLease) -> dict[str, object]:
        """The row's current ``content`` (still fenced on the lease)."""
        async with self._lock, self._sessions() as session:
            row = await _read(session, lease.post_id)
        if row is None or lease_of(row.metadata) != lease.lease_id:
            raise LeaseLostError(lease.post_id)
        return row.content

    async def merge_content(self, lease: GenerationLease, merge: ContentMerge) -> None:
        """Write ``merge(current content)``: an owner save made meanwhile is the
        base of the merge, never a conflict (the CAS loop re-reads on a race)."""
        await self._fenced(
            lease,
            _Mutation(lambda row: _content_values(row, merge(row.content)), bump=True),
        )

    async def finish(self, lease: GenerationLease, outcome: GenerationOutcome) -> None:
        """Record the final status/errors (metadata only)."""
        await self._fenced(
            lease,
            _Mutation(
                lambda row: {
                    "ai_generation_metadata": finished(row.metadata, outcome, _now())
                }
            ),
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
            if mutation.expect_version and row.lock_version != lease.lock_version:
                raise GenerationConflictError(lease.post_id)
            values = mutation.values(row)
            if mutation.bump:
                values["lock_version"] = row.lock_version + 1
            written = await _compare_and_set(session, (lease, row), values)
        if written and mutation.bump:
            lease.lock_version = row.lock_version + 1
        return written


def _content_values(row: _Row, write: ContentWrite) -> dict[str, object]:
    updated: dict[str, object] = {
        "content": write.content,
        "featured_image_url": write.featured_image_url,
        "ai_generation_metadata": with_voice_score(
            heartbeat(row.metadata, _now()), write.voice_score
        ),
    }
    if write.title:
        updated["title"] = write.title
    return updated


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
