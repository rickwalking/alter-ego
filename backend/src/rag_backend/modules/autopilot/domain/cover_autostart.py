"""The autopilot's automatic slide-1 cover generation port.

When a queued run starts a fresh carousel, the runner asks the scheduler for
one cover generation through the editorial facade's Grok images.edit path.
The scheduler decides (consent, photos, caps) and never raises: a skip or a
failure is logged, the run is never affected.
"""

from __future__ import annotations

from typing import Protocol


class AutoCoverScheduler(Protocol):
    """Enqueue one cover generation for a freshly created carousel."""

    async def start_cover(self, project_id: str) -> None:
        """Record and schedule the cover job, or skip with a log."""
        ...


__all__ = ["AutoCoverScheduler"]
