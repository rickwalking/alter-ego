"""``RecoveryStore`` for the daily scan: one short committed session per call.

A tried dead letter carries ``recovery_attempt`` in its payload; the retry keeps
the payload, so the scan never retries the same run twice. PgQueuer's log table
(its name from PgQueuer's own settings) exists only on Postgres; elsewhere its purge
is a no-op.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from pgqueuer.domain.settings import DBSettings
from sqlalchemy import (
    ColumnElement,
    CursorResult,
    and_,
    column,
    delete,
    func,
    select,
    table,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    KIND_AUTOPILOT_DRIVE,
    PAYLOAD_RECOVERY_ATTEMPT,
    RECOVERABLE_ERROR_CODES,
    SCAN_BATCH,
    STATUS_DEAD_LETTER,
    STATUS_SUCCEEDED,
)
from rag_backend.modules.generation_queue.domain.recovery import ParkedDrive
from rag_backend.modules.generation_queue.infrastructure.cutover import (
    orphaned_projects,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)

_G = GenerationRunModel
_POSTGRESQL = "postgresql"
_PGQ_LOG = table(str(DBSettings().queue_table_log), column("created"))


class SqlRecoveryStore:
    """Implements ``RecoveryStore``."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def recoverable(self, since: datetime) -> list[ParkedDrive]:
        """Untried autopilot dead letters since ``since`` (transient-class codes)."""
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(_G)
                    .where(
                        _G.kind == KIND_AUTOPILOT_DRIVE,
                        _G.status == STATUS_DEAD_LETTER,
                        _G.finished_at >= since,
                        _G.last_error_code.in_(RECOVERABLE_ERROR_CODES),
                        _G.autopilot_run_id.is_not(None),
                    )
                    .order_by(_G.finished_at, _G.id)
                )
            ).scalars()
            untried = [
                ParkedDrive(
                    generation_run_id=row.id, autopilot_run_id=str(row.autopilot_run_id)
                )
                for row in rows
                if not (row.payload or {}).get(PAYLOAD_RECOVERY_ATTEMPT)
            ]
            return untried[:SCAN_BATCH]

    async def mark_attempted(self, generation_run_id: UUID) -> bool:
        """Mark the dead letter tried once (compare-and-set); False when already."""
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(_G).where(_G.id == generation_run_id).with_for_update()
                )
            ).scalar_one_or_none()
            if row is None or row.status != STATUS_DEAD_LETTER:
                return False
            payload = dict(row.payload or {})
            if payload.get(PAYLOAD_RECOVERY_ATTEMPT):
                return False
            payload[PAYLOAD_RECOVERY_ATTEMPT] = True
            result = await session.execute(
                update(_G)
                .where(_G.id == generation_run_id, _G.status == STATUS_DEAD_LETTER)
                .values(payload=payload)
            )
            await session.commit()
            return cast(CursorResult[object], result).rowcount == 1

    async def dead_letters(self, since: datetime) -> int:
        """How many generation runs were dead-lettered since ``since``."""
        return await self._count(
            and_(_G.status == STATUS_DEAD_LETTER, _G.finished_at >= since)
        )

    async def active(self) -> int:
        """How many generation runs are queued, running or waiting for a retry."""
        return await self._count(_G.status.in_(ACTIVE_STATUSES))

    async def interactive_orphans(self) -> list[str]:
        """Titles of dashboard projects in progress with nothing queued."""
        async with self._sessions() as session:
            return [title for _, title in await orphaned_projects(session)]

    async def purge(self, before: datetime) -> tuple[int, int]:
        """Delete succeeded runs and PgQueuer log rows older than ``before``."""
        async with self._sessions() as session:
            runs = await session.execute(
                delete(_G).where(_G.status == STATUS_SUCCEEDED, _G.finished_at < before)
            )
            logs = 0
            if session.get_bind().dialect.name == _POSTGRESQL:
                purged = await session.execute(
                    delete(_PGQ_LOG).where(_PGQ_LOG.c.created < before)
                )
                logs = cast(CursorResult[object], purged).rowcount
            await session.commit()
            return cast(CursorResult[object], runs).rowcount, logs

    async def _count(self, condition: ColumnElement[bool]) -> int:
        async with self._sessions() as session:
            counted = await session.scalar(
                select(func.count()).select_from(_G).where(condition)
            )
            return int(counted or 0)


__all__ = ["SqlRecoveryStore"]
