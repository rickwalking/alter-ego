"""The PgQueuer side of the queue (pinned ``pgqueuer==1.6.0``).

A job's payload is the id of the generation run it carries, nothing else: the
payload of record lives in ``generation_runs``. Only this module and the worker
entry import PgQueuer, so the in-house fallback of ADR-0026 would replace this
file and the worker entry, not the callers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.types import JobId

from rag_backend.modules.generation_queue.constants import ENTRYPOINT
from rag_backend.modules.generation_queue.domain.models import GenerationRun, HeldJob

_ACTIVE_JOB_SQL = (
    "SELECT id FROM {table} WHERE dedupe_key = $1"
    " AND status IN ('queued', 'picked') ORDER BY id LIMIT 1"
)
_EXISTING_SQL = "SELECT id FROM {table} WHERE id = ANY($1::bigint[])"
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
        """Enqueue; None when PgQueuer already has an active job with the key."""
        ids = await self._queries.enqueue(
            ENTRYPOINT,
            job_payload(run.id),
            dedupe_key=run.dedupe_key,
            on_conflict="skip",
        )
        first = ids[0] if ids else None
        return int(first) if first is not None else None

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


__all__ = ["PgQueuerJobQueue", "job_payload", "run_id_of"]
