"""Ports the executors drive: the autopilot runner and the editorial workflow.

Implemented in infrastructure through the autopilot and editorial public facades,
so the queue never reaches into another module's internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.modules.generation_queue.domain.models import WorkflowResumePayload


@dataclass(frozen=True, kw_only=True)
class AutopilotView:
    """What the drive loop needs to know about an autopilot run."""

    state: str
    project_id: str | None
    phase: str


class AutopilotStepper(Protocol):
    """Reads and steps one autopilot run, each call in its own committed session."""

    async def view(self, run_id: str) -> AutopilotView | None:
        """The run's state, project and current phase key; None when missing."""
        ...

    async def step(self, run_id: str) -> int:
        """One runner step for this run. 0 when there was nothing to do now."""
        ...


class ProjectRecovery(Protocol):
    """Takes back a project whose driver died, from the checkpoint."""

    async def current_phase(self, project_id: str) -> str:
        """The project's current workflow phase ('' when unknown)."""
        ...

    async def in_progress(self, project_id: str) -> bool:
        """True when the project row says a phase is running."""
        ...

    async def reap(self, project_id: str) -> bool:
        """Park the orphaned run now (fence + mirror the checkpoint)."""
        ...

    async def redrive_if_parked(self, project_id: str) -> bool:
        """Re-run the node the checkpoint is parked before. False when none."""
        ...


class WorkflowResumer(Protocol):
    """Runs a dashboard resume through the run-owned editorial wrapper."""

    async def resume(self, payload: WorkflowResumePayload) -> None:
        """Run the phase inline; failures are marked on the row, not raised."""
        ...
