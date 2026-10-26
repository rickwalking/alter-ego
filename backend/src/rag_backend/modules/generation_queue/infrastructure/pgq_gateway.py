"""The PgQueuer side of the queue (pinned ``pgqueuer==1.6.0``).

A job's payload is the id of the generation run it carries, nothing else: the
payload of record lives in ``generation_runs``. PgQueuer access is isolated to
this module, the maintenance gateway and worker entry, so the in-house fallback
would replace those adapters, not the callers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.types import JobId

from rag_backend.modules.generation_queue.constants import (
    ENTRYPOINT,
    PAYLOAD_MANUAL_ACCELERATE_JOB_ID,
    PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID,
    PAYLOAD_MANUAL_CANCEL_JOB_ID,
)
from rag_backend.modules.generation_queue.domain.models import GenerationRun, HeldJob
from rag_backend.modules.generation_queue.domain.priority import priority_of

_ACTIVE_JOB_SQL = (
    "SELECT id FROM {table} WHERE dedupe_key = $1"
    " AND status IN ('queued', 'picked') ORDER BY id LIMIT 1"
)
_EXISTING_SQL = "SELECT id FROM {table} WHERE id = ANY($1::bigint[])"
_ACCELERATE_SQL = (
    "UPDATE {table} SET priority = GREATEST(priority, $2), execute_after = NOW()"
    " WHERE id = $1 AND dedupe_key = $3 AND status = 'queued' RETURNING id"
)
_PICKED_SQL = (
    "SELECT id FROM {table} WHERE id = $1 AND dedupe_key = $2"
    " AND status = 'picked' FOR UPDATE"
)
_FENCE_SQL = (
    "SELECT id FROM generation_runs WHERE id = $1 AND status = 'queued'"
    " AND pgq_job_id = $2 AND payload->>'attempt_id' = $3 FOR UPDATE"
)
_QUEUED_SQL = (
    "SELECT id FROM generation_runs WHERE id = $1 AND status = 'queued' FOR UPDATE"
)
_BEGIN = "BEGIN"
_COMMIT = "COMMIT"
_ROLLBACK = "ROLLBACK"
_HELD_ORDER: Literal["ASC"] = "ASC"
_ID = "id"


def job_payload(run_id: UUID) -> bytes:
    """The job payload for a generation run."""
    return str(run_id).encode()


def run_id_of(payload: bytes | None) -> UUID | None:
    """The generation run a job carries; None for a foreign or broken payload."""
    if not payload:
        return None
    try:
        return UUID(payload.decode())
    except (UnicodeDecodeError, ValueError):
        return None


class PgQueuerJobQueue:
    """Implements ``JobQueue`` on PgQueuer's ``Queries``."""

    def __init__(self, queries: Queries) -> None:
        self._queries = queries
        self._table = queries.qbe.settings.qualified.queue_table

    async def find_job(self, dedupe_key: str) -> int | None:
        """The queued or picked job carrying ``dedupe_key``."""
        rows = await self._queries.driver.fetch(
            _ACTIVE_JOB_SQL.format(table=self._table), dedupe_key
        )
        return int(str(rows[0][_ID])) if rows else None

    async def enqueue(self, run: GenerationRun) -> int | None:
        """Insert at payload priority, or raise an existing job without demotion."""
        ids = await self._queries.enqueue(
            ENTRYPOINT,
            job_payload(run.id),
            priority=priority_of(run.payload),
            dedupe_key=run.dedupe_key,
            on_conflict="update_priority",
        )
        first = ids[0] if ids else None
        return int(first) if first is not None else None

    async def kick(self, run: GenerationRun) -> int | None:
        """Accelerate queued work or cancel and replace a fenced picked job."""
        job_id = run.pgq_job_id
        if job_id is None:
            return await self._find_or_enqueue(run)
        if _has_job_marker(run) and await self._accelerate(run):
            return job_id
        if _cancel_fenced(run):
            replacement = await self._replace_picked(run)
            if replacement is not None:
                return replacement
        if job_id in await self.existing([job_id]):
            return job_id
        return await self._find_or_enqueue(run)

    async def _accelerate(self, run: GenerationRun) -> bool:
        rows = await self._queries.driver.fetch(
            _ACCELERATE_SQL.format(table=self._table),
            run.pgq_job_id,
            priority_of(run.payload),
            run.dedupe_key,
        )
        return bool(rows)

    async def _replace_picked(self, run: GenerationRun) -> int | None:
        await self._queries.driver.execute(_BEGIN)
        try:
            replacement = await self._replace_locked(run)
        except Exception:
            await self._queries.driver.execute(_ROLLBACK)
            raise
        if replacement is None:
            await self._queries.driver.execute(_ROLLBACK)
            return None
        await self._queries.driver.execute(_COMMIT)
        return replacement

    async def _replace_locked(self, run: GenerationRun) -> int | None:
        if not await self._fence_current(run):
            return None
        rows = await self._queries.driver.fetch(
            _PICKED_SQL.format(table=self._table), run.pgq_job_id, run.dedupe_key
        )
        if not rows:
            return run.pgq_job_id if await self._accelerate(run) else None
        if run.pgq_job_id is None:
            return None
        await self._queries.mark_job_as_cancelled([JobId(run.pgq_job_id)])
        return await self.enqueue(run)

    async def _fence_current(self, run: GenerationRun) -> bool:
        rows = await self._queries.driver.fetch(
            _FENCE_SQL, run.id, run.pgq_job_id, str(run.attempt_id)
        )
        return bool(rows)

    async def _find_or_enqueue(self, run: GenerationRun) -> int | None:
        await self._queries.driver.execute(_BEGIN)
        try:
            job_id = await self._enqueue_current(run)
        except Exception:
            await self._queries.driver.execute(_ROLLBACK)
            raise
        if job_id is None:
            await self._queries.driver.execute(_ROLLBACK)
            return None
        await self._queries.driver.execute(_COMMIT)
        return job_id

    async def _enqueue_current(self, run: GenerationRun) -> int | None:
        rows = await self._queries.driver.fetch(_QUEUED_SQL, run.id)
        if not rows:
            return None
        existing = await self.find_job(run.dedupe_key)
        if existing is not None:
            return existing
        return await self.enqueue(run)

    async def existing(self, job_ids: Sequence[int]) -> set[int]:
        """Which of these jobs are still in the queue table."""
        if not job_ids:
            return set()
        rows = await self._queries.driver.fetch(
            _EXISTING_SQL.format(table=self._table), list(job_ids)
        )
        return {int(str(row[_ID])) for row in rows}

    async def held(self, limit: int) -> list[HeldJob]:
        """Jobs held as ``failed``, oldest first."""
        jobs = await self._queries.list_failed_jobs(limit, _HELD_ORDER)
        return [
            HeldJob(job_id=int(job.id), generation_run_id=run_id_of(job.payload))
            for job in jobs
        ]

    async def forget(self, job_id: int) -> None:
        """Drop a held job once mirrored (logged as cancelled, deleted)."""
        await self._queries.mark_job_as_cancelled([JobId(job_id)])


def _has_job_marker(run: GenerationRun) -> bool:
    keys = (PAYLOAD_MANUAL_ACCELERATE_JOB_ID, PAYLOAD_MANUAL_CANCEL_JOB_ID)
    return any(run.payload.get(key) == run.pgq_job_id for key in keys)


def _cancel_fenced(run: GenerationRun) -> bool:
    if run.payload.get(PAYLOAD_MANUAL_CANCEL_JOB_ID) != run.pgq_job_id:
        return False
    value = run.payload.get(PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID)
    if not isinstance(value, str):
        return False
    try:
        cancelled = UUID(value)
        current = run.attempt_id
    except ValueError:
        return False
    return current is not None and current != cancelled


__all__ = ["PgQueuerJobQueue", "job_payload", "run_id_of"]
