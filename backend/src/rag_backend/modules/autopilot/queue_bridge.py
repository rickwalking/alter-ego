"""What the generation queue may do with autopilot runs.

The queue worker drives autopilot runs through these calls only: read a run,
step it once, park it with a reason, sweep expiries, list the runs that need
driving. Each call opens its own session and commits it, like one worker tick.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.modules.autopilot.application.backlog_promotion import (
    PromotionDependencies,
    promote_waiting,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.run_revive import (
    ReviveDependencies,
    revive,
)
from rag_backend.modules.autopilot.application.runner import AutopilotRunner
from rag_backend.modules.autopilot.bootstrap import (
    AutopilotTickConfig,
    runner_dependencies,
)
from rag_backend.modules.autopilot.constants import REASON_RUN_STALE
from rag_backend.modules.autopilot.domain.dead_letter import is_dead_letter
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog
from rag_backend.modules.autopilot.infrastructure.backlog_store import SqlBacklogStore
from rag_backend.modules.autopilot.infrastructure.dead_letter_runs import (
    SqlDeadLetterRuns,
)
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.notice_source import SqlNoticeLogStore
from rag_backend.modules.autopilot.infrastructure.queue_control import SqlQueueControl
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.queue_constants import (
    DAILY_RECOVERY_NOTICE_KEY,
    REASON_DAILY_RECOVERY,
    STALE_REVIVE_MIN_AGE_MINUTES,
)

if TYPE_CHECKING:
    from rag_backend.modules.generation_queue.public import ParkedDrive

DRIVEN_STATES: tuple[AutopilotRunState, ...] = (
    AutopilotRunState.QUEUED,
    AutopilotRunState.GENERATING,
    AutopilotRunState.REWORKING,
)


@dataclass(frozen=True, kw_only=True)
class AutopilotRunFacts:
    """State and project of one autopilot run."""

    state: str
    project_id: str | None


@dataclass(frozen=True, kw_only=True)
class AutopilotQueueBridge:
    """Runner access for the generation worker.

    ``retryable`` names the errors the queue retries with backoff; any other
    engine error is contained by the runner as before (the run is escalated).
    """

    config: AutopilotTickConfig
    sessions: async_sessionmaker[AsyncSession]
    retryable: Callable[[BaseException], bool]

    async def facts(self, run_id: str) -> AutopilotRunFacts | None:
        """The run's state and project, or None when it does not exist."""
        async with self.sessions() as session:
            run = await SqlAlchemyAutopilotRepository(session).get(UUID(run_id))
        if run is None:
            return None
        return AutopilotRunFacts(
            state=run.state.value, project_id=run.carousel_project_id
        )

    async def step(self, run_id: str) -> int:
        """One runner step for this run, committed. 0 when nothing happened."""
        async with self.sessions() as session:
            runner = self._runner(session)
            run = await SqlAlchemyAutopilotRepository(session).get(UUID(run_id))
            if run is None or run.state not in DRIVEN_STATES:
                return 0
            stepped = await runner.step(run)
            await session.commit()
            return stepped

    async def park(self, run_id: str, reason: str) -> None:
        """End an active run with ``reason`` (state change + owner notice)."""
        async with self.sessions() as session:
            run = await SqlAlchemyAutopilotRepository(session).get(UUID(run_id))
            if run is not None:
                await self._runner(session).park(run, reason)
            await session.commit()

    async def sweep(self) -> int:
        """Expire stale reviews, close or wake escalations."""
        async with self.sessions() as session:
            moved = await self._runner(session).sweep()
            await session.commit()
            return moved

    async def promote_backlog(self) -> int:
        """Queue waiting backlog themes into today's free slots; how many."""
        async with self.sessions() as session:
            return await promote_waiting(
                PromotionDependencies(
                    store=SqlAlchemyTopicIntakeStore(session),
                    backlog=SqlBacklogStore(session),
                    clock=SystemClock(),
                    daily_cap=self.config.daily_cap,
                )
            )

    async def revive_dead_letter(self, drive: ParkedDrive) -> bool:
        """Atomically mark and retry one parked drive, once per theme.

        False when the run is gone, no longer parked by the queue (Pedro already
        retried or discarded it), is itself the scan's earlier retry, or was
        already marked by a concurrent scan. The autopilot lock uses the same
        write order as the owner retry, so the two paths cannot double-revive.
        """
        async with self.sessions() as session:
            run = await _locked_run(session, drive.autopilot_run_id)
            from rag_backend.modules.generation_queue.public import (
                mark_recovery_attempt,
            )

            marked = await mark_recovery_attempt(session, drive.generation_run_id)
            if not marked:
                return False
            if run is None or not is_dead_letter(run.state_reason) or _recovered(run):
                await session.commit()
                return False
            return await _revive_once(session, run)

    async def revive_stale(self, since: datetime) -> int:
        """Resume runs escalated as ``run_stale`` since ``since``, once each.

        A run escalated in the last hour is left for the next scan (the reaper may
        not be done with it); each run moves in its own transaction.
        """
        until = SystemClock().now() - timedelta(minutes=STALE_REVIVE_MIN_AGE_MINUTES)
        async with self.sessions() as session:
            result = await session.execute(
                select(AutopilotRunModel.id)
                .where(
                    AutopilotRunModel.state == AutopilotRunState.ESCALATED.value,
                    AutopilotRunModel.state_reason == REASON_RUN_STALE,
                    AutopilotRunModel.updated_at >= since,
                    AutopilotRunModel.updated_at <= until,
                )
                .order_by(AutopilotRunModel.updated_at)
            )
            run_ids = [row[0] for row in result.all()]
        revived = 0
        for run_id in run_ids:
            async with self.sessions() as session:
                run = await SqlAlchemyAutopilotRepository(session).get(run_id)
                if run is not None and not _recovered(run):
                    revived += int(await _revive_once(session, run))
        return revived

    async def active_run_ids(self, limit: int) -> list[tuple[str, str | None]]:
        """Runs that need driving, oldest first."""
        async with self.sessions() as session:
            result = await session.execute(
                select(AutopilotRunModel.id, AutopilotRunModel.carousel_project_id)
                .where(AutopilotRunModel.state.in_([s.value for s in DRIVEN_STATES]))
                .order_by(AutopilotRunModel.created_at)
                .limit(limit)
            )
            return [(str(row[0]), row[1]) for row in result.all()]

    def _runner(self, session: AsyncSession) -> AutopilotRunner:
        deps = runner_dependencies(session, self.config)
        return AutopilotRunner(replace(deps, retryable=self.retryable))


async def _locked_run(session: AsyncSession, run_id: str) -> AutopilotRun | None:
    """Read one run after locking its row against a concurrent revive."""
    result = await session.execute(
        select(AutopilotRunModel.id)
        .where(AutopilotRunModel.id == UUID(run_id))
        .with_for_update()
    )
    if result.scalar_one_or_none() is None:
        return None
    return await SqlAlchemyAutopilotRepository(session).get(UUID(run_id))


def _recovered(run: AutopilotRun) -> bool:
    return DAILY_RECOVERY_NOTICE_KEY in run.notice_log.statuses


async def _revive_once(session: AsyncSession, run: AutopilotRun) -> bool:
    """Revive ``run``, mark the queued run so the scan never retries it again."""
    queued_id = await revive(_revive_deps(session), run, REASON_DAILY_RECOVERY)
    if queued_id is not None:
        queued = await SqlAlchemyAutopilotRepository(session).get(queued_id)
        if queued is not None:
            statuses = (*queued.notice_log.statuses, DAILY_RECOVERY_NOTICE_KEY)
            await SqlNoticeLogStore(session).save(
                SaveNoticeLog(
                    run_id=queued_id,
                    log=replace(queued.notice_log, statuses=statuses),
                )
            )
    await session.commit()
    return queued_id is not None


def _revive_deps(session: AsyncSession) -> ReviveDependencies:
    return ReviveDependencies(
        runs=SqlAlchemyAutopilotRepository(session),
        clock=SystemClock(),
        queue=SqlQueueControl(session),
        dead_letters=SqlDeadLetterRuns(session),
    )


__all__ = ["DRIVEN_STATES", "AutopilotQueueBridge", "AutopilotRunFacts"]
