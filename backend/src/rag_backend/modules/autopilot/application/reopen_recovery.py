"""Send a scheduled run back for review when its carousel's review was reopened.

Pedro's decision (2026-11-02): a slide-1 change on a scheduled carousel drops
the approval and the API layer asks for a new review (``reopened``). That ask
can be lost: the process dies between the switch's commit and the hook. The
run would then wait in ``scheduled`` and expire at its time with no review
ever sent. On every due tick, a ``scheduled`` run whose time is still ahead
and whose carousel is back in final review (a draft waiting for a human, not
released) moves ``scheduled -> reworking`` with its time kept, as the hook
would have done; the worker then sends the review once the render settled.

A run scheduled in the last ``REOPEN_RECOVERY_GRACE_SECONDS`` is left alone:
an owner's schedule tap claims ``scheduled`` before its approve lands, so the
carousel is briefly a draft then.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from rag_backend.modules.autopilot.cover_constants import (
    REASON_COVER_REVIEW_REOPENED,
    REOPEN_RECOVERY_GRACE_SECONDS,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    Clock,
    PublishCheckpoint,
)
from rag_backend.modules.autopilot.domain.schedule_ports import (
    DueScheduleQuery,
    ScheduledRunSource,
)
from rag_backend.modules.autopilot.schedule_constants import SCHEDULE_SCAN_LIMIT

_S = AutopilotRunState


class ReopenedReviewSource(Protocol):
    """Whether a carousel is back in final review after a dropped approval."""

    async def reopened(self, project_id: str) -> bool:
        """A completed draft waiting in final review, not released."""
        ...


@dataclass(frozen=True, kw_only=True)
class ReopenRecoveryDeps:
    """The run store, the scheduled runs, the carousel read, commit, clock."""

    runs: AutopilotRunRepository
    scheduled: ScheduledRunSource
    reviews: ReopenedReviewSource
    checkpoint: PublishCheckpoint
    clock: Clock


class ReopenRecovery:
    """Recover the review request of reopened carousels' scheduled runs."""

    def __init__(self, deps: ReopenRecoveryDeps) -> None:
        self._deps = deps

    async def tick(self) -> int:
        """How many runs went back for review. Each move commits on its own."""
        now = self._deps.clock.now()
        query = DueScheduleQuery(now=now, limit=SCHEDULE_SCAN_LIMIT)
        settled = now - timedelta(seconds=REOPEN_RECOVERY_GRACE_SECONDS)
        moved = 0
        for run in await self._deps.scheduled.waiting(query):
            if run.updated_at is not None and run.updated_at > settled:
                continue
            moved += await self._recover(run)
        return moved

    async def _recover(self, run: AutopilotRun) -> int:
        project_id = run.carousel_project_id
        if project_id is None or not await self._deps.reviews.reopened(project_id):
            return 0
        moved = await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=_S.SCHEDULED,
                new=_S.REWORKING,
                reason=REASON_COVER_REVIEW_REOPENED,
                updated_at=run.updated_at,
            )
        )
        await self._deps.checkpoint.commit()
        return int(moved)


__all__ = ["ReopenRecovery", "ReopenRecoveryDeps", "ReopenedReviewSource"]
