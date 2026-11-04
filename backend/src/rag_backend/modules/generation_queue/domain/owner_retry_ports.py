"""Ports and results of the owner's carousel Retry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.modules.generation_queue.domain.owner_retry import (
    OwnerRetryCommand,
    RetryFacts,
    RetryKind,
    RetryRefusal,
)


@dataclass(frozen=True, kw_only=True)
class RetryPlan:
    """An accepted decision, with the feedback line a revise sends."""

    command: OwnerRetryCommand
    facts: RetryFacts
    kind: RetryKind
    reason: str
    feedback: str = ""


@dataclass(frozen=True, kw_only=True)
class RetryWrite:
    """The store's verdict: the staged state, or the refusal that rolled it back."""

    refusal: RetryRefusal | None = None
    lock_version: int | None = None
    phase: str = ""
    phase_status: str = ""
    autopilot_run_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class RetryAuditCommand:
    """The allowlisted fields of one ``carousel.retry.requested`` event."""

    plan: RetryPlan
    write: RetryWrite


@dataclass(frozen=True, kw_only=True)
class RetryResult:
    """The service result the website route and the Telegram button map."""

    accepted: bool
    kind: RetryKind | None = None
    refusal: RetryRefusal | None = None
    phase: str = ""
    phase_status: str = ""
    lock_version: int | None = None
    autopilot_run_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class RetryCapability:
    """Whether a Retry would be accepted now, and as which kind."""

    can_retry: bool
    kind: RetryKind | None = None
    refusal: RetryRefusal | None = None
    lock_version: int | None = None


class OwnerRetryStore(Protocol):
    """Fresh facts under the row lock and one savepoint-scoped write."""

    async def read(self, command: OwnerRetryCommand) -> RetryFacts | None:
        """Lock the carousel row and gather the facts; None when it is missing."""
        ...

    async def apply(self, plan: RetryPlan) -> RetryWrite:
        """CAS, stage, move the escalated run; a refusal leaves nothing behind."""
        ...

    async def commit(self) -> None:
        """Commit the Retry and its audit together."""
        ...

    async def rollback(self) -> None:
        """Roll back a refused Retry and release the row lock."""
        ...


class OwnerRetryAudit(Protocol):
    """The workflow audit/outbox path, on the Retry's session."""

    async def record(self, command: RetryAuditCommand) -> None:
        """Write one ``carousel.retry.requested`` event."""
        ...


__all__ = [
    "OwnerRetryAudit",
    "OwnerRetryStore",
    "RetryAuditCommand",
    "RetryCapability",
    "RetryPlan",
    "RetryResult",
    "RetryWrite",
]
