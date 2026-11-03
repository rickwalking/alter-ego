"""Ports and commands for run recovery (QA round 1).

Rework queued by the webhook, the lock version recorded on escalation, the
rollback the runner needs before it records an engine failure, and the settle
of an abandoned escalation's carousel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.domain.models import AutopilotRun


@dataclass(frozen=True, kw_only=True)
class ReworkIntent:
    """The owner's rework, stored for the runner to apply."""

    run_id: UUID
    phase: str
    feedback: str


@dataclass(frozen=True, kw_only=True)
class EscalationMark:
    """Workflow lock version at the moment the run was escalated."""

    run_id: UUID
    version: int


@dataclass(frozen=True, kw_only=True)
class EscalatedScan:
    """How many escalated runs one sweep checks (QA r2 R1)."""

    limit: int


@dataclass(frozen=True, kw_only=True)
class WakeCheck:
    """When the sweep last looked at an escalated run's carousel."""

    run_id: UUID
    at: datetime


@dataclass(frozen=True, kw_only=True)
class UnnotifiedMark:
    """A fixed escalation that cannot be woken because no notifier is set."""

    run_id: UUID
    at: datetime


@dataclass(frozen=True, kw_only=True)
class CarouselSettle:
    """An abandoned escalation's carousel and the lock version it escalated at.

    ``idle_hours`` is the window the run sat unfixed (recorded on the event).
    """

    project_id: str
    expected_version: int
    idle_hours: int


class CarouselSettler(Protocol):
    """Rejects an abandoned escalation's carousel. The caller commits."""

    async def settle_abandoned(self, settle: CarouselSettle) -> bool:
        """Reject the carousel if it still waits for a human at the version.

        False, and nothing written, when it is no longer waiting or was changed
        since. A failure never undoes the caller's own writes.
        """
        ...


class RunRecoveryStore(Protocol):
    """Recovery writes on ``autopilot_runs``. The caller commits."""

    async def queue_rework(self, intent: ReworkIntent) -> bool:
        """Store the intent while the run is ``reworking``. False otherwise."""
        ...

    async def clear_rework(self, run_id: UUID) -> None:
        """Forget the queued rework once it was applied or abandoned."""
        ...

    async def mark_escalated(self, mark: EscalationMark) -> None:
        """Remember the lock version the run was escalated at."""
        ...

    async def escalated_for_check(self, scan: EscalatedScan) -> list[AutopilotRun]:
        """Escalated runs, least recently checked first, so none is starved."""
        ...

    async def mark_checked(self, check: WakeCheck) -> None:
        """Record the check time. Leaves ``state`` and ``updated_at`` alone."""
        ...

    async def mark_unnotified(self, mark: UnnotifiedMark) -> bool:
        """Set reason ``notifier_unconfigured`` and ``updated_at`` (QA r3 Q3)."""
        ...

    async def rollback(self) -> None:
        """Discard this unit of work after an unclassified engine error."""
        ...
