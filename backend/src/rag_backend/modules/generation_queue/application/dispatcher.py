"""The dispatcher: from our outbox rows to PgQueuer jobs, and back for failures.

One pass (every 10 s in the worker):

1. Safety net: every autopilot run in an active state with no active generation
   run gets one staged (runs from before the deploy, a stage that was missed).
2. Hand-over: queued rows without a job are enqueued; a crash between the enqueue
   and recording the job id is resolved by looking the job up by dedupe key first.
3. Lost jobs: an active row whose job no longer exists (deleted by an operator, a
   cancelled job) loses its job id, so step 2 hands it over again.
4. Reconciler: jobs PgQueuer holds as ``failed`` without our handler having
   mirrored them become ``dead_letter`` with one Telegram notice, then the held job
   is dropped (the row is the record; a retry stages a fresh job).

Each step is idempotent, so two dispatchers or a re-run pass change nothing twice.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.modules.generation_queue.constants import (
    DISPATCH_BATCH,
    ERROR_HELD_JOB,
    ERROR_MESSAGE_MAX_CHARS,
    LOG_DISPATCHED,
)
from rag_backend.modules.generation_queue.domain.models import (
    DeadLetterCommand,
    GenerationRun,
    HeldJob,
    autopilot_stage,
)
from rag_backend.modules.generation_queue.domain.ports import (
    ActiveAutopilotSource,
    DeadLetterNotices,
    GenerationRunStore,
    JobQueue,
)

logger = structlog.get_logger()


@dataclass(frozen=True)
class DispatchReport:
    """What one pass did."""

    staged: int = 0
    dispatched: int = 0
    lost: int = 0
    dead_lettered: int = 0


@dataclass(frozen=True, kw_only=True)
class DispatcherDependencies:
    """Collaborators of one dispatcher pass."""

    store: GenerationRunStore
    queue: JobQueue
    autopilot: ActiveAutopilotSource
    notices: DeadLetterNotices


class Dispatcher:
    """Stage, hand over, recover lost jobs, mirror held failures."""

    def __init__(self, deps: DispatcherDependencies) -> None:
        self._deps = deps

    async def run_once(self) -> DispatchReport:
        """One idempotent pass."""
        return DispatchReport(
            staged=await self._stage_missing(),
            dispatched=await self._hand_over(),
            lost=await self._recover_lost(),
            dead_lettered=await self._mirror_held(),
        )

    async def _stage_missing(self) -> int:
        staged = 0
        for run_id, project_id in await self._deps.autopilot.active_run_ids(
            DISPATCH_BATCH
        ):
            if await self._deps.store.stage(autopilot_stage(run_id, project_id)):
                staged += 1
        return staged

    async def _hand_over(self) -> int:
        dispatched = 0
        for run in await self._deps.store.undispatched(DISPATCH_BATCH):
            job_id = await self._job_for(run)
            if job_id is None:
                continue
            await self._deps.store.set_job(run.id, job_id)
            logger.info(LOG_DISPATCHED, generation_run_id=str(run.id), job_id=job_id)
            dispatched += 1
        return dispatched

    async def _job_for(self, run: GenerationRun) -> int | None:
        existing = await self._deps.queue.find_job(run.dedupe_key)
        if existing is not None:
            return existing
        return await self._deps.queue.enqueue(run)

    async def _recover_lost(self) -> int:
        runs = await self._deps.store.dispatched_active(DISPATCH_BATCH)
        job_ids = [run.pgq_job_id for run in runs if run.pgq_job_id is not None]
        alive = await self._deps.queue.existing(job_ids)
        lost = [run for run in runs if run.pgq_job_id not in alive]
        for run in lost:
            await self._deps.store.clear_job(run.id)
        return len(lost)

    async def _mirror_held(self) -> int:
        mirrored = 0
        for job in await self._deps.queue.held(DISPATCH_BATCH):
            if await self._mirror(job):
                mirrored += 1
            await self._deps.queue.forget(job.job_id)
        return mirrored

    async def _mirror(self, job: HeldJob) -> bool:
        if job.generation_run_id is None:
            return False
        run = await self._deps.store.get(job.generation_run_id)
        if run is None:
            return False
        moved = await self._deps.store.mark_dead_letter(
            DeadLetterCommand(
                run_id=run.id,
                error_code=ERROR_HELD_JOB,
                error=job.error[:ERROR_MESSAGE_MAX_CHARS],
            )
        )
        if moved:
            await self._deps.notices.stage(run, ERROR_HELD_JOB)
        return moved


__all__ = ["DispatchReport", "Dispatcher", "DispatcherDependencies"]
