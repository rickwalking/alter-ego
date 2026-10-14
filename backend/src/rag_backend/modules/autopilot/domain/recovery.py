"""Ports and commands for run recovery (AE-0348 QA round 1).

Rework queued by the webhook, the lock version recorded on escalation, and
the rollback the runner needs before it records an engine failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


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

    async def rollback(self) -> None:
        """Discard this unit of work after an unclassified engine error."""
        ...
