"""The morning backlog promotion on PgQueuer's scheduler.

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from rag_backend.modules.autopilot.queue_constants import (
    BACKLOG_PROMOTION_CRON_UTC,
    BACKLOG_PROMOTION_ENTRYPOINT,
)
from rag_backend.modules.generation_queue.domain.maintenance import MaintenanceEnqueue
from rag_backend.worker.schedules import (
    register_backlog_promotion,
    run_backlog_promotion,
)

Job = Callable[[object], Awaitable[None]]


@dataclass
class _Bridge:
    promoted: int = 2
    fail: bool = False
    calls: int = 0

    async def promote_backlog(self) -> int:
        self.calls += 1
        if self.fail:
            raise RuntimeError("database down")
        return self.promoted


@dataclass
class _Scheduler:
    registered: list[tuple[str, str]] = field(default_factory=list)
    jobs: list[Job] = field(default_factory=list)

    def schedule(self, entrypoint: str, expression: str) -> Callable[[Job], Job]:
        self.registered.append((entrypoint, expression))

        def keep(job: Job) -> Job:
            self.jobs.append(job)
            return job

        return keep


@dataclass
class _Control:
    calls: int = 0

    async def request_full(self) -> MaintenanceEnqueue:
        self.calls += 1
        return MaintenanceEnqueue(job_id=1, inserted=True)


async def test_the_morning_promotion_is_scheduled_at_eight_five() -> None:
    """Scenario: Promotion cron enqueues the shared full control job at 08:05."""
    scheduler, bridge, control = _Scheduler(), _Bridge(), _Control()
    register_backlog_promotion(scheduler, control)
    assert scheduler.registered == [(BACKLOG_PROMOTION_ENTRYPOINT, "5 11 * * *")]
    assert BACKLOG_PROMOTION_CRON_UTC == "5 11 * * *"
    local = datetime(2026, 10, 24, 11, 5, tzinfo=UTC).astimezone(
        ZoneInfo("America/Sao_Paulo")
    )
    assert (local.hour, local.minute) == (8, 5)
    await scheduler.jobs[0](object())
    assert bridge.calls == 0
    assert control.calls == 1


async def test_a_failed_promotion_is_logged_not_raised() -> None:
    """Scenario: Waiting themes start in the morning even without a scout batch"""
    assert await run_backlog_promotion(_Bridge(promoted=2)) == 2
    assert await run_backlog_promotion(_Bridge(fail=True)) is None
