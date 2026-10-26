"""In-memory collaborators for manual recovery service tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace

from rag_backend.modules.autopilot.domain.queue_position import QueuePosition
from rag_backend.modules.generation_queue.domain.errors import DriveLockBusyError
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    AuditCommand,
    MaintenanceNotice,
    ManualReprocessCommand,
    RecoveryMutation,
    RecoverySnapshot,
    RecoveryWrite,
)
from rag_backend.modules.generation_queue.domain.models import GenerationRun


@dataclass
class FakeManualStore:
    """A scripted manual recovery store."""

    snapshot: RecoverySnapshot
    write: RecoveryWrite
    events: list[str] = field(default_factory=list)
    existing: GenerationRun | None = None
    snapshots: list[RecoverySnapshot] = field(default_factory=list)
    apply_calls: int = 0
    rollback_calls: int = 0
    position_result: QueuePosition | None = None

    async def load(self, command: ManualReprocessCommand) -> RecoverySnapshot:
        """Return the next fresh snapshot, then keep returning the last one."""
        if self.snapshots:
            self.snapshot = self.snapshots.pop(0)
        self.snapshot = replace(self.snapshot, command=command)
        return self.snapshot

    async def find_existing(self, snapshot: RecoverySnapshot) -> GenerationRun | None:
        """Return the scripted compatible active manual run."""
        del snapshot
        return self.existing

    async def apply(self, mutation: RecoveryMutation) -> RecoveryWrite:
        """Record one attempted mutation and return the scripted result."""
        del mutation
        self.apply_calls += 1
        return self.write

    async def position(self, run: GenerationRun) -> QueuePosition | None:
        """Return the scripted shared placement."""
        del run
        return self.position_result

    async def commit(self) -> None:
        """Record the transaction boundary."""
        self.events.append("commit")

    async def rollback(self) -> None:
        """Record a refusal rollback."""
        self.rollback_calls += 1
        self.events.append("rollback")


@dataclass
class FakeRecoveryAudit:
    """Audit commands and their event order."""

    events: list[str] = field(default_factory=list)
    commands: list[AuditCommand] = field(default_factory=list)

    async def record(self, command: AuditCommand) -> None:
        """Record one safe audit command."""
        self.commands.append(command)
        self.events.append("audit")


@dataclass
class FakeMaintenanceNotifier:
    """A notifier that can succeed, decline or fail."""

    events: list[str] = field(default_factory=list)
    notices: list[MaintenanceNotice] = field(default_factory=list)
    notified: bool = True
    error: Exception | None = None

    async def notify(self, notice: MaintenanceNotice) -> bool:
        """Record a post-commit maintenance request."""
        self.notices.append(notice)
        self.events.append("notify")
        if self.error is not None:
            raise self.error
        return self.notified


@dataclass
class FakeDriveLock:
    """Record complete lock sets and optionally report a busy drive."""

    held: list[list[str]] = field(default_factory=list)
    busy: bool = False

    @asynccontextmanager
    async def hold(self, keys: Sequence[str]) -> AsyncIterator[None]:
        """Hold the supplied keys without waiting."""
        self.held.append(list(keys))
        if self.busy:
            raise DriveLockBusyError
        yield
