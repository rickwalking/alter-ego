"""Dispatch-only and full maintenance execution semantics."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from rag_backend.modules.generation_queue.application.dispatcher import DispatchReport
from rag_backend.modules.generation_queue.application.maintenance import (
    MaintenanceDependencies,
    MaintenanceExecutor,
)
from rag_backend.modules.generation_queue.domain.maintenance import (
    MaintenanceCommand,
    MaintenanceOutcome,
    parse_maintenance,
)
from rag_backend.modules.generation_queue.domain.recovery import ScanReport


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
        yield self.acquired
        self.events.append("unlock")


@dataclass
class _Steps:
    events: list[str]

    async def promote(self) -> int:
        self.events.append("promote")
        return 1

    async def recover(self) -> ScanReport:
        self.events.append("recover")
        return ScanReport()


def _executor(
    acquired: bool = True,
) -> tuple[MaintenanceExecutor, _Dispatcher, list[str]]:
    events: list[str] = []
    dispatcher = _Dispatcher(events)
    steps = _Steps(events)
    executor = MaintenanceExecutor(
        MaintenanceDependencies(
            dispatcher=dispatcher,
            lock=_Lock(events, acquired),
            promotion=steps.promote,
            recovery=steps.recover,
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
    assert events == ["lock", "promote", "recover", "dispatch", "unlock"]


async def test_busy_full_pass_does_no_work_and_sends_no_summary() -> None:
    """Scenario: A busy full-pass claimant exits before any scheduled function."""
    executor, dispatcher, events = _executor(acquired=False)
    outcome = await executor.execute(MaintenanceCommand().payload)
    assert outcome is MaintenanceOutcome.BUSY
    assert dispatcher.kicked == []
    assert events == ["lock", "unlock"]


async def test_invalid_or_foreign_control_payload_is_ignored() -> None:
    """Scenario: A foreign maintenance payload cannot invoke queue operations."""
    executor, dispatcher, events = _executor()
    assert await executor.execute(None) is MaintenanceOutcome.IGNORED
    assert await executor.execute(b"dispatch:not-a-uuid") is MaintenanceOutcome.IGNORED
    assert dispatcher.kicked == []
    assert events == []


def test_control_payloads_carry_complete_dedupe_identities() -> None:
    """Scenario: Dispatch and full jobs keep distinct, complete dedupe payloads."""
    run_id = uuid4()
    dispatch = MaintenanceCommand(run_id=run_id)
    full = MaintenanceCommand()
    assert dispatch.dedupe_key == f"dispatch:{run_id}"
    assert dispatch.payload == f"dispatch:{run_id}".encode()
    assert full.dedupe_key == "full"
    assert full.payload == b"full"
    assert parse_maintenance(dispatch.payload) == dispatch
    assert parse_maintenance(full.payload) == full
    assert parse_maintenance(b"other") is None
