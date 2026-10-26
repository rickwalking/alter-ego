"""Concurrent double-click behavior for failed-terminal replacements."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

from rag_backend.modules.generation_queue.application.manual_reprocess import (
    ManualRecoveryDependencies,
    ManualRecoveryService,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    RecoveryMutation,
    RecoveryOutcome,
    RecoveryPolicy,
    RecoverySnapshot,
    RecoveryWrite,
    StuckKind,
    WriteStatus,
)
from rag_backend.modules.generation_queue.domain.models import GenerationStatus
from tests.unit.modules.generation_queue.manual_recovery_fakes import (
    FakeDriveLock,
    FakeMaintenanceNotifier,
    FakeRecoveryAudit,
)
from tests.unit.modules.generation_queue.queue_fakes import (
    FixedClock,
    make_run,
    resume_run,
)


@dataclass
class _RaceState:
    original_id: UUID
    replacement_id: UUID
    loads: int = 0
    reads: int = 0
    loaded: asyncio.Event = field(default_factory=asyncio.Event)
    read: asyncio.Event = field(default_factory=asyncio.Event)
    mutex: asyncio.Lock = field(default_factory=asyncio.Lock)
    replacement: object = None


class _RaceStore:
    """Both callers read the dead original before one CAS wins."""

    def __init__(self, state: _RaceState, snapshot: RecoverySnapshot) -> None:
        self._state = state
        self._snapshot = snapshot

    async def load(self, command: ManualReprocessCommand) -> RecoverySnapshot:
        """Synchronize both initial reads before either request can mutate."""
        del command
        self._state.loads += 1
        if self._state.loads == 2:
            self._state.loaded.set()
        await self._state.loaded.wait()
        return self._snapshot

    async def find_existing(self, snapshot: RecoverySnapshot) -> object:
        """Synchronize the idempotency reads, then link the replacement."""
        del snapshot
        self._state.reads += 1
        if self._state.reads == 2:
            self._state.read.set()
        await self._state.read.wait()
        return self._state.replacement

    async def apply(self, mutation: RecoveryMutation) -> RecoveryWrite:
        """Allow exactly one replacement; the CAS loser receives its identity."""
        del mutation
        async with self._state.mutex:
            if self._state.replacement is not None:
                return RecoveryWrite(
                    status=WriteStatus.EXISTING,
                    run=self._state.replacement,
                    lock_version=5,
                )
            replacement = resume_run(
                id=self._state.replacement_id,
                status=GenerationStatus.QUEUED,
                payload={
                    "manual_origin": "carousel_reprocess",
                    "manual_stuck_kind": "dead_letter",
                    "replaces_generation_run_id": str(self._state.original_id),
                },
            )
            self._state.replacement = replacement
            return RecoveryWrite(
                status=WriteStatus.APPLIED, run=replacement, lock_version=5
            )

    async def commit(self) -> None:
        """Each request has its own transaction boundary."""

    async def rollback(self) -> None:
        """No refusal is expected in this race."""


async def test_concurrent_clicks_share_successor_and_one_audit() -> None:
    """Scenario: Concurrent clicks return one linked run and one audit event."""
    original = make_run(status=GenerationStatus.DEAD_LETTER)
    command = ManualReprocessCommand(
        project_id=None,
        run_id=original.id,
        actor_id="admin",
        expected_version=None,
    )
    snapshot = RecoverySnapshot(
        command=command,
        run=original,
        project=None,
        latest_run_id=original.id,
        active_run_id=None,
        autopilot_dead=True,
    )
    state = _RaceState(original_id=original.id, replacement_id=uuid4())
    audit = FakeRecoveryAudit()
    notifier = FakeMaintenanceNotifier()
    services = []
    for _ in range(2):
        store = _RaceStore(state, snapshot)
        services.append(
            ManualRecoveryService(
                ManualRecoveryDependencies(
                    store=store,
                    audit=audit,
                    lock=FakeDriveLock(),
                    notifier=notifier,
                    clock=FixedClock(),
                    policy=RecoveryPolicy(
                        heartbeat_stale_seconds=180, dispatcher_grace_seconds=600
                    ),
                )
            )
        )
    results = await asyncio.gather(
        *(
            service.reprocess(replace(command, request_id=uuid4()))
            for service in services
        )
    )
    assert {result.outcome for result in results} == {
        RecoveryOutcome.QUEUED,
        RecoveryOutcome.EXISTING,
    }
    assert {result.run.id for result in results} == {state.replacement_id}
    assert all(result.stuck_kind is StuckKind.DEAD_LETTER for result in results)
    assert len(audit.commands) == 1
    assert len(notifier.notices) == 2
    assert {notice.run_id for notice in notifier.notices} == {state.replacement_id}
