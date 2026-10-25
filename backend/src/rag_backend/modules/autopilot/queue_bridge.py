"""What the generation queue may do with autopilot runs.

The queue worker drives autopilot runs through these calls only: read a run,
step it once, park it with a reason, sweep expiries, list the runs that need
driving. Each call opens its own session and commits it, like one worker tick.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.modules.autopilot.application.backlog_promotion import (
    PromotionDependencies,
    promote_waiting,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.runner import AutopilotRunner
from rag_backend.modules.autopilot.bootstrap import (
    AutopilotTickConfig,
    runner_dependencies,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.backlog_store import SqlBacklogStore
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)

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


__all__ = ["DRIVEN_STATES", "AutopilotQueueBridge", "AutopilotRunFacts"]
