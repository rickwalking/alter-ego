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


__all__ = ["CarouselCheckpointPhaseStatusReader", "CarouselStaleRunReaper"]
