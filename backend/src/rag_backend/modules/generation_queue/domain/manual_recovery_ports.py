"""Outbound ports isolated from the generation worker's run store."""

from __future__ import annotations

from typing import Protocol

from rag_backend.modules.generation_queue.domain.manual_recovery import (
    AuditCommand,
    MaintenanceNotice,
    ManualReprocessCommand,
    RecoveryMutation,
    RecoverySnapshot,
    RecoveryWrite,
)
from rag_backend.modules.generation_queue.domain.models import GenerationRun


class ManualRecoveryStore(Protocol):
    """Fresh reads and one caller-session atomic recovery write."""

    async def load(self, command: ManualReprocessCommand) -> RecoverySnapshot:
        """Load the target and currently attributed project."""
        ...

    async def find_existing(self, snapshot: RecoverySnapshot) -> GenerationRun | None:
        """Find a compatible active manual run, including a replacement."""
        ...

    async def apply(self, mutation: RecoveryMutation) -> RecoveryWrite:
        """Serialize, CAS and link the accepted or existing run."""
        ...

    async def commit(self) -> None:
        """Commit the recovery and audit atomically."""
        ...

    async def rollback(self) -> None:
        """Roll back a refused or losing write."""
        ...


class ManualRecoveryAudit(Protocol):
    """The existing workflow audit/outbox path."""

    async def record(self, command: AuditCommand) -> None:
        """Write one safe audit and outbox record in the same session."""
        ...


class MaintenanceNotifier(Protocol):
    """The durable dispatch-only maintenance entrypoint."""

    async def notify(self, notice: MaintenanceNotice) -> bool:
        """Return whether the worker accepted the post-commit notification."""
        ...


__all__ = ["MaintenanceNotifier", "ManualRecoveryAudit", "ManualRecoveryStore"]
