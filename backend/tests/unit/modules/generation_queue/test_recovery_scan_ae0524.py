"""The daily recovery scan's orchestration, summary and worker registration.

Feature: backend/tests/features/daily_recovery_scan_ae0524.feature
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.generation_queue.application.recovery_scan import (
    DailyRecoveryScan,
    DailyScanDependencies,
    summary_text,
)
from rag_backend.modules.generation_queue.constants import (
    SCAN_CRON_UTC,
    SCAN_ENTRYPOINT,
)
from rag_backend.modules.generation_queue.domain.maintenance import MaintenanceEnqueue
from rag_backend.modules.generation_queue.domain.recovery import (
    ParkedDrive,
    ScanReport,
)
from rag_backend.worker.recovery import register_daily_scan, run_daily_scan

_NOW = datetime(2026, 10, 24, 7, 0, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _Store:
    parked: list[ParkedDrive] = field(default_factory=list)
    tried: set[UUID] = field(default_factory=set)
    since: list[datetime] = field(default_factory=list)
    purged_before: list[datetime] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)

    async def recoverable(self, since: datetime) -> list[ParkedDrive]:
        self.since.append(since)
        return [d for d in self.parked if d.generation_run_id not in self.tried]

    async def mark_attempted(self, generation_run_id: UUID) -> bool:
        if generation_run_id in self.tried:
            return False
        self.tried.add(generation_run_id)
        return True

    async def dead_letters(self, since: datetime) -> int:
        self.since.append(since)
        return len(self.parked) - len(self.tried)

    async def active(self) -> int:
        return 3

    async def interactive_orphans(self) -> list[str]:
        return list(self.orphans)

    async def purge(self, before: datetime) -> tuple[int, int]:
        self.purged_before.append(before)
        return 4, 9


@dataclass
class _Autopilot:
    resolved: set[str] = field(default_factory=set)
    revived: list[str] = field(default_factory=list)
    stale_since: list[datetime] = field(default_factory=list)
    stale: int = 0
    store: _Store | None = None

    async def revive_dead_letter(self, drive: ParkedDrive) -> bool:
        if self.store is None or not await self.store.mark_attempted(
            drive.generation_run_id
        ):
            return False
        if drive.autopilot_run_id in self.resolved:
            return False
        self.revived.append(drive.autopilot_run_id)
        return True

    async def revive_stale(self, since: datetime) -> int:
        self.stale_since.append(since)
        return self.stale


def _scan(store: _Store, autopilot: _Autopilot) -> DailyRecoveryScan:
    autopilot.store = store
    return DailyRecoveryScan(
        DailyScanDependencies(store=store, autopilot=autopilot, clock=_Clock())
    )


def _drive() -> ParkedDrive:
    return ParkedDrive(generation_run_id=uuid4(), autopilot_run_id=str(uuid4()))


async def test_a_recent_transient_dead_letter_is_retried_once() -> None:
    """Scenario: A recent transient dead letter is retried once"""
    drive = _drive()
    store, autopilot = _Store(parked=[drive]), _Autopilot()
    report = await _scan(store, autopilot).run_once()
    assert autopilot.revived == [drive.autopilot_run_id]
    assert store.tried == {drive.generation_run_id}
    assert store.since == [_NOW - timedelta(days=7)] * 2
    assert report.recovered == 1


async def test_a_second_scan_retries_nothing_again() -> None:
    """Scenario: A second scan the same day retries nothing again"""
    drive = _drive()
    store, autopilot = _Store(parked=[drive]), _Autopilot()
    await _scan(store, autopilot).run_once()
    again = await _scan(store, autopilot).run_once()
    assert autopilot.revived == [drive.autopilot_run_id]
    assert again.recovered == 0


async def test_a_dead_letter_pedro_resolved_is_not_retried() -> None:
    """Scenario: A dead letter Pedro already resolved is not retried"""
    drive = _drive()
    store = _Store(parked=[drive])
    autopilot = _Autopilot(resolved={drive.autopilot_run_id})
    report = await _scan(store, autopilot).run_once()
    assert report.recovered == 0
    assert store.tried == {drive.generation_run_id}


async def test_stale_escalations_are_resumed_and_counted() -> None:
    """Scenario: A stale autopilot escalation resumes from its checkpoint"""
    store, autopilot = _Store(), _Autopilot(stale=2)
    report = await _scan(store, autopilot).run_once()
    assert autopilot.stale_since == [_NOW - timedelta(hours=72)]
    assert report.recovered == 2


async def test_the_scan_purges_counts_and_lists_parked_projects() -> None:
    """Scenario: Old succeeded runs and PgQueuer logs are purged"""
    store = _Store(parked=[_drive(), _drive()], orphans=["Projeto parado"])
    report = await _scan(store, _Autopilot(resolved=set())).run_once()
    assert store.purged_before == [_NOW - timedelta(days=30)]
    assert (report.purged_runs, report.purged_logs) == (4, 9)
    assert report.queued == 3
    assert report.still_dead == 0
    assert report.interactive == ("Projeto parado",)


def test_the_summary_gives_the_counts_and_the_parked_projects() -> None:
    """Scenario: Pedro receives one summary"""
    plain = summary_text(ScanReport(recovered=2, still_dead=1, queued=5))
    assert plain == (
        "🌅 Varredura diária da fila: 2 recolocado(s) na fila, "
        "1 parado(s) nos últimos 7 dias, 5 na fila agora."
    )
    long_title = "x" * 120
    listed = summary_text(
        ScanReport(interactive=(long_title, *(f"p{i}" for i in range(12))))
    )
    second = listed.splitlines()[1]
    assert second.startswith("Projetos do painel parados (retome pelo editor): ")
    assert "x" * 79 + "…" in second
    assert "p8" in second
    assert "p9" not in second


def test_parked_dashboard_projects_are_listed_not_resumed() -> None:
    """Scenario: Parked dashboard projects are listed, not resumed"""
    text = summary_text(ScanReport(interactive=("Carrossel do painel",)))
    assert text.endswith(
        "Projetos do painel parados (retome pelo editor): Carrossel do painel"
    )


async def test_the_worker_sends_one_summary_per_scan() -> None:
    """Scenario: Pedro receives one summary"""
    sent: list[str] = []
    report = await run_daily_scan(_scan(_Store(), _Autopilot()), sent.append)
    assert report is not None
    assert len(sent) == 1
    assert sent[0].startswith("🌅 Varredura diária da fila")


async def test_a_failed_scan_sends_nothing_and_does_not_raise() -> None:
    """Scenario: A failed scan is logged and tried again the next day"""

    class _Broken(_Store):
        async def purge(self, before: datetime) -> tuple[int, int]:
            raise RuntimeError(before)

    sent: list[str] = []
    assert await run_daily_scan(_scan(_Broken(), _Autopilot()), sent.append) is None
    assert sent == []


@dataclass
class _Scheduler:
    registered: list[tuple[str, str]] = field(default_factory=list)
    jobs: list[Callable[[object], Awaitable[None]]] = field(default_factory=list)

    def schedule(
        self, entrypoint: str, expression: str
    ) -> Callable[
        [Callable[[object], Awaitable[None]]], Callable[[object], Awaitable[None]]
    ]:
        self.registered.append((entrypoint, expression))

        def keep(
            job: Callable[[object], Awaitable[None]],
        ) -> Callable[[object], Awaitable[None]]:
            self.jobs.append(job)
            return job

        return keep


@dataclass
class _Control:
    calls: int = 0

    async def request_full(self) -> MaintenanceEnqueue:
        self.calls += 1
        return MaintenanceEnqueue(job_id=1, inserted=True)


async def test_the_daily_scan_is_scheduled_at_four_in_sao_paulo() -> None:
    """Scenario: Cron enqueues the shared full control job at 04:00 São Paulo."""
    scheduler, control = _Scheduler(), _Control()
    register_daily_scan(scheduler, control)
    assert scheduler.registered == [(SCAN_ENTRYPOINT, SCAN_CRON_UTC)]
    assert SCAN_CRON_UTC == "0 7 * * *"
    await scheduler.jobs[0](object())
    assert control.calls == 1


@pytest.mark.parametrize("hours", [0, 3])
def test_seven_utc_is_four_in_sao_paulo(hours: int) -> None:
    """Scenario: The daily scan is scheduled at 04:00 São Paulo time"""
    from zoneinfo import ZoneInfo

    moment = datetime(2026, 1 + hours, 15, 7, 0, tzinfo=UTC)
    assert moment.astimezone(ZoneInfo("America/Sao_Paulo")).hour == 4
