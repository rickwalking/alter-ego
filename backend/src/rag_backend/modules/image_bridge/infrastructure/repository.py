"""SQLAlchemy ``ImageBridgeJobRepository``.

Each call opens its own short session and commits, so the long-running
waiter never holds a transaction while it polls. Transitions are single
conditional UPDATEs (``WHERE status = 'pending'``): concurrent writers on
different workers cannot both win.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.dml import Delete, Update

from rag_backend.modules.image_bridge.constants import (
    ERROR_MESSAGE_MAX_CHARS,
    JOB_RETENTION_DAYS,
)
from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJob,
    ImageBridgeJobStatus,
    JobDeadline,
    JobFailure,
    JobSuccess,
)
from rag_backend.modules.image_bridge.infrastructure.models import (
    ImageBridgeJobModel,
)

SessionMakerProvider = Callable[[], async_sessionmaker[AsyncSession]]

_PENDING = ImageBridgeJobStatus.PENDING.value


class SqlImageBridgeJobRepository:
    """Postgres (SQLite in unit tests) job store."""

    def __init__(self, session_maker: SessionMakerProvider) -> None:
        """``session_maker`` is a provider, not a maker: the engine exists only
        after ``init_db``.
        """
        self._session_maker = session_maker

    async def create(self, job: ImageBridgeJob) -> None:
        """Insert a new pending job."""
        async with self._session_maker()() as session:
            session.add(_row_from(job))
            await session.commit()

    async def get(self, job_id: UUID) -> ImageBridgeJob | None:
        """The job without its image bytes, or ``None``."""
        async with self._session_maker()() as session:
            row = await session.get(ImageBridgeJobModel, job_id)
            return _job_from(row) if row is not None else None

    async def succeed(self, success: JobSuccess) -> bool:
        """Store the image if the job is pending and not yet overdue."""
        statement = (
            _pending_update(success.job_id)
            .where(ImageBridgeJobModel.expires_at > success.at)
            .values(
                status=ImageBridgeJobStatus.SUCCEEDED.value,
                image_bytes=success.image,
                completed_at=success.at,
            )
        )
        return await self._changed(statement)

    async def fail(self, failure: JobFailure) -> bool:
        """Mark a pending job failed."""
        statement = _pending_update(failure.job_id).values(
            status=ImageBridgeJobStatus.FAILED.value,
            error_code=failure.code,
            error_message=failure.message[:ERROR_MESSAGE_MAX_CHARS],
            completed_at=failure.at,
        )
        return await self._changed(statement)

    async def expire(self, deadline: JobDeadline) -> bool:
        """Mark a pending job expired."""
        statement = _pending_update(deadline.job_id).values(
            status=ImageBridgeJobStatus.EXPIRED.value, completed_at=deadline.at
        )
        return await self._changed(statement)

    async def take_image(self, job_id: UUID) -> bytes | None:
        """Read the image bytes once and null them in the same transaction."""
        async with self._session_maker()() as session:
            image = await session.scalar(
                select(ImageBridgeJobModel.image_bytes)
                .where(ImageBridgeJobModel.id == job_id)
                .with_for_update()
            )
            await session.execute(
                update(ImageBridgeJobModel)
                .where(ImageBridgeJobModel.id == job_id)
                .values(image_bytes=None)
            )
            await session.commit()
            return image

    async def sweep(self, now: datetime) -> None:
        """Expire overdue pending jobs; delete rows past the retention window."""
        expire_overdue = (
            update(ImageBridgeJobModel)
            .where(
                ImageBridgeJobModel.status == _PENDING,
                ImageBridgeJobModel.expires_at <= now,
            )
            .values(status=ImageBridgeJobStatus.EXPIRED.value, completed_at=now)
        )
        cutoff = now - timedelta(days=JOB_RETENTION_DAYS)
        purge = delete(ImageBridgeJobModel).where(
            ImageBridgeJobModel.created_at < cutoff
        )
        async with self._session_maker()() as session:
            await session.execute(expire_overdue)
            await session.execute(purge)
            await session.commit()

    async def _changed(self, statement: Update | Delete) -> bool:
        async with self._session_maker()() as session:
            result = await session.execute(statement)
            await session.commit()
            return _rowcount(result) == 1


def _pending_update(job_id: UUID) -> Update:
    return update(ImageBridgeJobModel).where(
        ImageBridgeJobModel.id == job_id, ImageBridgeJobModel.status == _PENDING
    )


def _rowcount(result: object) -> int:
    return result.rowcount if isinstance(result, CursorResult) else 0


def _row_from(job: ImageBridgeJob) -> ImageBridgeJobModel:
    return ImageBridgeJobModel(
        id=job.id,
        status=job.status.value,
        size=job.size,
        token_sha256=job.token_sha256,
        created_at=job.created_at,
        expires_at=job.expires_at,
    )


def _job_from(row: ImageBridgeJobModel) -> ImageBridgeJob:
    return ImageBridgeJob(
        id=row.id,
        status=ImageBridgeJobStatus(row.status),
        size=row.size,
        token_sha256=row.token_sha256,
        created_at=_aware(row.created_at),
        expires_at=_aware(row.expires_at),
        completed_at=_aware(row.completed_at) if row.completed_at else None,
        error_code=row.error_code,
        error_message=row.error_message,
    )


def _aware(moment: datetime) -> datetime:
    """SQLite drops the offset; Postgres timestamptz keeps it."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
