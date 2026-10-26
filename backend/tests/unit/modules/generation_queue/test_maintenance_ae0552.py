"""Dispatch and mode-specific maintenance execution semantics."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from structlog.testing import capture_logs

from rag_backend.modules.generation_queue.application.dispatcher import DispatchReport
from rag_backend.modules.generation_queue.application.maintenance import (
    MaintenanceDependencies,
    MaintenanceExecutor,
)
from rag_backend.modules.generation_queue.constants import (
    LOG_MAINTENANCE_BUSY,
    MAINTENANCE_CONCURRENCY_LIMIT,
    MAINTENANCE_ENTRYPOINT,
)
from rag_backend.modules.generation_queue.domain.maintenance import (
    MaintenanceCommand,
    MaintenanceMode,
    MaintenanceOutcome,
    parse_maintenance,
)
from rag_backend.modules.generation_queue.domain.recovery import ScanReport
from rag_backend.worker import maintenance as worker_maintenance
from rag_backend.worker.maintenance import WorkerMaintenance


@dataclass
class _Dispatcher:
    events: list[str]
    kicked: list[UUID] = field(default_factory=list)

    async def kick(self, run_id: UUID) -> bool:
        self.events.append("kick")
        self.kicked.append(run_id)
        return True

    async def run_once(self) -> DispatchReport:
        self.events.append("dispatch")
        return DispatchReport()


@dataclass
class _Lock:
    events: list[str]
    acquired: bool = True

    @asynccontextmanager
    async def hold(self) -> AsyncIterator[bool]:
        self.events.append("lock")
        try:
            yield self.acquired
        finally:
            self.events.append("unlock")


@dataclass
class _Steps:
    events: list[str]
    full_active: bool = False
    recovery_fails: bool = False

    async def promote(self) -> int:
        self.events.append("promote")
        return 1

    async def recover(self) -> ScanReport:
        self.events.append("recover")
        if self.recovery_fails:
            raise RuntimeError("scan failed")
        return ScanReport()

    async def full_is_active(self) -> bool:
        return self.full_active

    async def supersede_queued_scheduled(self) -> None:
        self.events.append("supersede")


def _executor(
    acquired: bool = True,
    full_active: bool = False,
    recovery_fails: bool = False,
) -> tuple[MaintenanceExecutor, _Dispatcher, list[str]]:
    events: list[str] = []
    dispatcher = _Dispatcher(events)
    steps = _Steps(events, full_active, recovery_fails)
    executor = MaintenanceExecutor(
        MaintenanceDependencies(
            dispatcher=dispatcher,
            lock=_Lock(events, acquired),
            promotion=steps.promote,
            recovery=steps.recover,
            coordination=steps,
        )
    )
    return executor, dispatcher, events


async def test_dispatch_kicks_one_run_then_runs_the_normal_pass() -> None:
    """Scenario: Reprocessar kicks dispatch without promotion or recovery."""
    run_id = uuid4()
    executor, dispatcher, events = _executor()
    outcome = await executor.execute(MaintenanceCommand(run_id=run_id).payload)
    assert outcome is MaintenanceOutcome.DISPATCHED
    assert dispatcher.kicked == [run_id]
    assert events == ["kick", "dispatch"]


async def test_full_pass_shares_one_lock_and_one_ordered_summary_path() -> None:
    """Scenario: Process queue now shares maintenance locks with schedules."""
    executor, _, events = _executor()
    outcome = await executor.execute(MaintenanceCommand().payload)
    assert outcome is MaintenanceOutcome.COMPLETED
    assert events == ["lock", "promote", "recover", "dispatch", "supersede", "unlock"]


@pytest.mark.parametrize("mode", [MaintenanceMode.PROMOTE, MaintenanceMode.SCAN])
async def test_scheduled_work_yields_to_an_active_full_pass(
    mode: MaintenanceMode,
) -> None:
    """Scenario: Full maintenance subsumes queued scheduled passes"""
    executor, dispatcher, events = _executor(full_active=True)
    command = MaintenanceCommand(mode=mode)
    assert await executor.execute(command.payload) is MaintenanceOutcome.SUBSUMED
    assert dispatcher.kicked == []
    assert events == []


async def test_failed_full_pass_keeps_scheduled_work_available() -> None:
    """Scenario: Full maintenance subsumes queued scheduled passes"""
    executor, _, events = _executor(recovery_fails=True)
    with pytest.raises(RuntimeError, match="scan failed"):
        await executor.execute(MaintenanceCommand().payload)
    assert events == ["lock", "promote", "recover", "unlock"]


async def test_dispatch_is_not_subsumed_by_an_active_full_pass() -> None:
    """Scenario: Full maintenance subsumes queued scheduled passes"""
    run_id = uuid4()
    executor, dispatcher, events = _executor(full_active=True)
    outcome = await executor.execute(MaintenanceCommand(run_id=run_id).payload)
    assert outcome is MaintenanceOutcome.DISPATCHED
    assert dispatcher.kicked == [run_id]
    assert events == ["kick", "dispatch"]


async def test_scheduled_promotion_never_revives_purges_or_sends_summary() -> None:
    """Scenario: The morning promotion is scheduled at 08:05 São Paulo time"""
    executor, _, events = _executor()
    command = MaintenanceCommand(mode=MaintenanceMode.PROMOTE)
    assert await executor.execute(command.payload) is MaintenanceOutcome.COMPLETED
    assert events == ["lock", "promote", "unlock"]


async def test_scheduled_scan_never_promotes() -> None:
    """Scenario: The daily scan is scheduled at 04:00 São Paulo time"""
    executor, _, events = _executor()
    command = MaintenanceCommand(mode=MaintenanceMode.SCAN)
    assert await executor.execute(command.payload) is MaintenanceOutcome.COMPLETED
    assert events == ["lock", "recover", "unlock"]


@pytest.mark.parametrize("mode", list(MaintenanceMode))
async def test_busy_maintenance_logs_its_mode_and_does_no_work(
    mode: MaintenanceMode,
) -> None:
    """Scenario: Process queue now shares maintenance locks with schedules"""
    executor, dispatcher, events = _executor(acquired=False)
    command = MaintenanceCommand(mode=mode)
    with capture_logs() as logs:
        outcome = await executor.execute(command.payload)
    assert outcome is MaintenanceOutcome.BUSY
    assert dispatcher.kicked == []
    assert events == ["lock", "unlock"]
    assert [(entry["event"], entry["mode"]) for entry in logs] == [
        (LOG_MAINTENANCE_BUSY, mode.value)
    ]


async def test_invalid_or_foreign_control_payload_is_ignored() -> None:
    """Scenario: A foreign maintenance payload cannot invoke queue operations."""
    executor, dispatcher, events = _executor()
    assert await executor.execute(None) is MaintenanceOutcome.IGNORED
    assert await executor.execute(b"dispatch:not-a-uuid") is MaintenanceOutcome.IGNORED
    assert dispatcher.kicked == []
    assert events == []


def test_control_payloads_carry_complete_dedupe_identities() -> None:
    """Scenario: Maintenance control jobs are durable and deduped"""
    run_id = uuid4()
    dispatch = MaintenanceCommand(run_id=run_id)
    promote = MaintenanceCommand(mode=MaintenanceMode.PROMOTE)
    scan = MaintenanceCommand(mode=MaintenanceMode.SCAN)
    full = MaintenanceCommand()
    assert dispatch.dedupe_key == f"dispatch:{run_id}"
    assert dispatch.payload == f"dispatch:{run_id}".encode()
    assert (promote.dedupe_key, promote.payload) == ("promote", b"promote")
    assert (scan.dedupe_key, scan.payload) == ("scan", b"scan")
    assert full.dedupe_key == "full"
    assert full.payload == b"full"
    for command in (dispatch, promote, scan, full):
        assert parse_maintenance(command.payload) == command
    assert parse_maintenance(b"other") is None


@dataclass
class _Pgq:
    registrations: list[tuple[str, object]] = field(default_factory=list)

    def entrypoint(self, name: str, **kwargs: object) -> Callable[[object], object]:
        self.registrations.append((name, kwargs.get("concurrency_limit")))
        return lambda job: job

    def schedule(self, name: str, expression: str) -> Callable[[object], object]:
        del name, expression
        return lambda job: job


def test_maintenance_registration_serializes_control_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Full maintenance subsumes queued scheduled passes"""
    pgq = _Pgq()
    wiring = cast(
        WorkerMaintenance,
        SimpleNamespace(pgq=pgq, queries=object(), autopilot_enabled=False),
    )
    monkeypatch.setattr(worker_maintenance, "_executor", lambda _wiring: object())
    monkeypatch.setattr(
        worker_maintenance, "PgQueuerMaintenanceGateway", lambda _queries: object()
    )
    worker_maintenance.register_maintenance(wiring)
    assert pgq.registrations == [
        (MAINTENANCE_ENTRYPOINT, MAINTENANCE_CONCURRENCY_LIMIT)
    ]
