"""Protocols for the carousel stale-run reaper (AE-0315).

The workflow-workers tick depends on these domain contracts; the concrete
heartbeat query, checkpoint reconciliation, and fenced flip live in
infrastructure so the application/worker layer gains no new infrastructure
import (mirrors :mod:`workflow_timeout`).
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class CarouselCheckpointPhaseStatusReader(Protocol):
    """Reads a project's checkpoint-level phase_status (None when absent)."""

    async def __call__(self, project_id: str) -> str | None:
        """Return the checkpoint's phase_status for reap reconciliation."""
        ...


class CarouselStaleRunReaper(Protocol):
    """Liveness-keyed reaper for dead in_progress carousel runs."""

    async def tick(self, db: AsyncSession) -> int:
        """Run one watchdog observation pass; return the number of reaps.

        Rules (pinned by AE-0315): only ``phase_status == in_progress`` rows
        are ever considered; a NULL heartbeat is alert-only forever; a reap
        requires N consecutive stale observations; wall-clock age only
        alerts. The flip is ONE atomic UPDATE bumping ``lock_version`` and
        ``run_epoch`` and clearing the run columns; checkpoint state is
        never touched.
        """
        ...


class CarouselCheckpointStateGateway(Protocol):
    """Read/write a carousel's LangGraph checkpoint state (AE-0311 reconciler).

    Adapts ``CarouselWorkflowEngine`` so the drift reconciler stays free of an
    application/infrastructure → agents import; the engine's ``update_state``
    wrapper (``as_node`` inferred) is preserved.
    """

    async def read_state(self, project_id: str) -> dict[str, object] | None:
        """Return the checkpoint workflow state, or None when absent."""
        ...

    async def write_state(self, project_id: str, values: dict[str, object]) -> None:
        """Patch checkpoint state through the engine wrapper."""
        ...


class CarouselDriftReconciler(Protocol):
    """Auto-converges projection↔checkpoint drift for in-flight carousels."""

    async def reconcile(self, db: AsyncSession) -> int:
        """Converge in-flight rows whose repaired projection outran a stale
        blocking checkpoint report; return the number converged (AE-0311).
        """
        ...


class CarouselRepublishSweeper(Protocol):
    """Server-guaranteed republish of marked completed carousels (AE-0314).

    A post-completion slide edit stamps ``needs_republish_since`` transactionally
    and the client triggers the republish for fast feedback. This watchdog is the
    guarantee: it republishes any marked project whose marker is older than a few
    minutes (the client's own republish already cleared fresh ones) and clears the
    marker on success. Runs AFTER the drift reconciler in the tick.
    """

    async def sweep(self, db: AsyncSession) -> int:
        """Republish overdue-marked completed carousels; return the count."""
        ...


__all__ = [
    "CarouselCheckpointPhaseStatusReader",
    "CarouselCheckpointStateGateway",
    "CarouselDriftReconciler",
    "CarouselRepublishSweeper",
    "CarouselStaleRunReaper",
]
