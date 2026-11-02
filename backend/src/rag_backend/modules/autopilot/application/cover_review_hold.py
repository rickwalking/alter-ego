"""Hold an owner's Telegram review while a website cover changes slide 1.

Pedro's decision (2026-11-02): a cover the owner generates on the website for
a completed carousel in final review switches slide 1 and re-renders it. The
Telegram review on screen shows the old render and its buttons carry only the
run id, so the run must not stay in ``awaiting_owner`` meanwhile:

- ``hold``: ``awaiting_owner -> reworking`` (compare-and-set) with the
  ``website_cover`` rework queued (its feedback is the hold's start time), so
  the worker skips the run instead of driving it; ``updated_at``, the anchor of
  the review's 72-hour window, is kept;
- ``release(changed=True)``: the queued rework is cleared and the run stays in
  ``reworking``; the worker's normal final-review stop moves it back to
  ``awaiting_owner`` and sends the review again at the new lock version;
- ``release(changed=False)``: nothing changed on the carousel, so the run goes
  straight back to ``awaiting_owner`` with its window anchor kept, and the
  review on screen stays valid.

A run in any other state (a scheduled one included) is never held. Each step
commits on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.cover_constants import (
    COVER_REVIEW_HOLD_PHASE,
    REASON_COVER_REVIEW_HOLD,
    REASON_COVER_REVIEW_KEPT,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository, Clock
from rag_backend.modules.autopilot.domain.recovery import ReworkIntent, RunRecoveryStore

_S = AutopilotRunState


class Committer(Protocol):
    """Commits the session the ports write on."""

    async def commit(self) -> None: ...


@dataclass(frozen=True, kw_only=True)
class CoverReviewHoldDeps:
    """The run store, the rework store, the session commit and the clock."""

    runs: AutopilotRunRepository
    recovery: RunRecoveryStore
    checkpoint: Committer
    clock: Clock


class CoverReviewHold:
    """``hold`` / ``release`` around one website cover switch."""

    def __init__(self, deps: CoverReviewHoldDeps) -> None:
        self._deps = deps

    async def hold(self, project_id: str) -> UUID | None:
        """The held run, or None when no run waits for the owner's review."""
        run = await self._deps.runs.find_by_carousel(project_id)
        if run is None or run.state is not _S.AWAITING_OWNER:
            return None
        moved = await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=_S.AWAITING_OWNER,
                new=_S.REWORKING,
                reason=REASON_COVER_REVIEW_HOLD,
                updated_at=run.updated_at,
            )
        )
        if not moved:
            return None
        started = self._deps.clock.now().isoformat()
        await self._deps.recovery.queue_rework(
            ReworkIntent(
                run_id=run.run_id, phase=COVER_REVIEW_HOLD_PHASE, feedback=started
            )
        )
        await self._deps.checkpoint.commit()
        return run.run_id

    async def release(self, run_id: UUID, *, changed: bool) -> None:
        """Clear the hold; unchanged goes straight back to the owner's review."""
        await self._deps.recovery.clear_rework(run_id)
        run = await self._deps.runs.get(run_id)
        if not changed and run is not None:
            await self._deps.runs.transition(
                TransitionCommand(
                    run_id=run_id,
                    expected=_S.REWORKING,
                    new=_S.AWAITING_OWNER,
                    reason=REASON_COVER_REVIEW_KEPT,
                    updated_at=run.updated_at,
                )
            )
        await self._deps.checkpoint.commit()


__all__ = ["CoverReviewHold", "CoverReviewHoldDeps"]
