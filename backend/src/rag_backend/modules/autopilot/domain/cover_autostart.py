"""The autopilot's automatic slide-1 cover generation ports.

When a queued run starts a fresh carousel, the runner asks the scheduler for
one cover generation through the editorial facade's Grok images.edit path.
The scheduler decides (consent, photos, caps) and never raises: a skip or a
failure is logged, the run is never affected.

At each gate, before it resumes, the runner asks the applier to put that
cover on slide 1 once it succeeded, so the finalize render, and with it the
owner's first final review, already shows it.
"""

from __future__ import annotations

from typing import Protocol


class AutoCoverScheduler(Protocol):
    """Enqueue one cover generation for a freshly created carousel."""

    async def start_cover(self, project_id: str) -> None:
        """Record and schedule the cover job, or skip with a log."""
        ...


class AutoCoverApplier(Protocol):
    """Put the carousel's succeeded autopilot cover on slide 1 at a gate."""

    async def apply_cover(self, project_id: str) -> bool:
        """True when slide 1 just took it (the lock version moved); never raises."""
        ...


async def cover_at_gate(applier: AutoCoverApplier | None, project_id: str) -> bool:
    """True when the step stored the cover: the gate is read again before a resume."""
    if applier is None or not project_id:
        return False
    return await applier.apply_cover(project_id)


__all__ = ["AutoCoverApplier", "AutoCoverScheduler", "cover_at_gate"]
