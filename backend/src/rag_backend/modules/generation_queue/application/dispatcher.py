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
   is dropped (the row is the record; a retry stages a fresh job). A held job is
   mirrored only onto the row that still points at it: a row the owner already
   requeued has moved on to a new job and is left alone.

Each step is idempotent, so two dispatchers or a re-run pass change nothing twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from rag_backend.modules.generation_queue.application.generation_events import (
    NO_EVENT_RECORDER,
    NO_RUN_COMPLETION,
    generation_event_run,
    generation_event_scope,
    record_generation_event,
)
from rag_backend.modules.generation_queue.constants import (
    DISPATCH_BATCH,
    ERROR_HELD_JOB,
    ERROR_MESSAGE_MAX_CHARS,
    EVENT_RUN_DEAD_LETTER,
    EVENT_RUN_LOST,
    EVENT_RUN_QUEUED,
    LOG_DISPATCHED,
    MESSAGE_GENERATION_FAILED,
    MESSAGE_GENERATION_QUEUED,
    MESSAGE_GENERATION_RETRY,
    OUTCOME_DEAD_LETTER,
    OUTCOME_QUEUED,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRecorder,
    GenerationRunCompletion,
)
from rag_backend.modules.generation_queue.domain.models import (
    DeadLetterCommand,
    GenerationRun,
    GenerationStatus,
    HeldJob,
    autopilot_stage,
    is_active,
)
from rag_backend.modules.generation_queue.domain.ports import (
    ActiveAutopilotSource,
    DeadLetterNotices,
    GenerationRunStore,
    JobQueue,
)

logger = structlog.get_logger()
_ERROR_LOST_JOB = "job_lost"


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
    events: GenerationEventRecorder = NO_EVENT_RECORDER
    completion: GenerationRunCompletion = NO_RUN_COMPLETION


class Dispatcher:
    """Stage, hand over, recover lost jobs, mirror held failures."""

    def __init__(self, deps: DispatcherDependencies) -> None:
        self._deps = deps

    async def kick(self, run_id: UUID) -> bool:
        """Reconcile one queued run and persist its transport job id."""
        run = await self._deps.store.get(run_id)
        if run is None or run.status is not GenerationStatus.QUEUED:
            return False
        job_id = await self._deps.queue.kick(run)
        current = await self._deps.store.get(run_id)
        if job_id is None or current is None or not is_active(current.status):
            return False
        await self._deps.store.set_job(run.id, job_id)
        await self._record(
            run,
            GenerationEventInput(
                event_type=EVENT_RUN_QUEUED,
                outcome=OUTCOME_QUEUED,
                attempt=run.attempts + 1,
                message_code=MESSAGE_GENERATION_QUEUED,
                details={"action": "manual_kick"},
            ),
        )
        return True

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
            await self._record(
                run,
                GenerationEventInput(
                    event_type=EVENT_RUN_QUEUED,
                    outcome=OUTCOME_QUEUED,
                    attempt=run.attempts + 1,
                    message_code=MESSAGE_GENERATION_QUEUED,
                ),
            )
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
            await self._record(
                run,
                GenerationEventInput(
                    event_type=EVENT_RUN_LOST,
                    outcome=OUTCOME_QUEUED,
                    error_code=_ERROR_LOST_JOB,
                    message_code=MESSAGE_GENERATION_RETRY,
                ),
            )
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
        if run is None or run.pgq_job_id != job.job_id:
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
            await self._record(
                run,
                GenerationEventInput(
                    event_type=EVENT_RUN_DEAD_LETTER,
                    outcome=OUTCOME_DEAD_LETTER,
                    error_code=ERROR_HELD_JOB,
                    message_code=MESSAGE_GENERATION_FAILED,
                ),
            )
            if run.carousel_project_id is not None:
                await self._deps.completion.completed(
                    run.carousel_project_id, succeeded=False
                )
        return moved

    async def _record(self, run: GenerationRun, event: GenerationEventInput) -> None:
        async with generation_event_scope(generation_event_run(run), self._deps.events):
            await record_generation_event(event)


__all__ = ["DispatchReport", "Dispatcher", "DispatcherDependencies"]
