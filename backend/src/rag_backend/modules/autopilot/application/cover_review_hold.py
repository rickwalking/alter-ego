"""Hold an owner's Telegram review while a website cover changes slide 1.

Pedro's decision (2026-11-02): a cover the owner generates on the website for
a completed carousel in final review switches slide 1 and re-renders it. The
Telegram review on screen shows the old render and its buttons carry only the
run id, so the run must not stay in ``awaiting_owner`` meanwhile:

- ``hold``: ``awaiting_owner -> reworking`` (compare-and-set) with the
  ``website_cover`` rework queued (its feedback is the hold's start time), so
  the worker skips the run instead of driving it; ``updated_at``, the anchor of
  the review's 72-hour window, is kept; an open publish-time reply ("Outro
  horário") is dropped, since it answered the render being replaced;
- ``release(changed=True)``: the queued rework is cleared and the run stays in
  ``reworking``; the worker's normal final-review stop moves it back to
  ``awaiting_owner`` and sends the review again at the new lock version;
- ``release(changed=False)``: nothing changed on the carousel, so the run goes
  straight back to ``awaiting_owner`` with its window anchor kept, and the
  review on screen stays valid;
- ``escalate``: the switch could not be confirmed (a failed rollback): the run
  goes ``reworking -> escalated`` with the lock version marked, so the owner is
  told and no review of a render slide 1 may not match goes out.

- ``reopened``: the switch dropped an approved carousel's approval (Pedro's
  decision, 2026-11-02): a ``scheduled`` run (its ``scheduled_at`` kept) or an
  ``awaiting_owner`` one goes to ``reworking`` with its window anchor kept, and
  the worker's final-review stop sends the review again at the new lock
  version; a held run is already on that way.

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
    REASON_COVER_REVIEW_REOPENED,
    REASON_COVER_REVIEW_UNSAFE,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.notice_log import is_time_reply, set_pending
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    Clock,
    NoticeLogStore,
)
from rag_backend.modules.autopilot.domain.recovery import (
    EscalationMark,
    ReworkIntent,
    RunRecoveryStore,
)

_S = AutopilotRunState
_REOPENABLE = frozenset({_S.SCHEDULED, _S.AWAITING_OWNER})


class Committer(Protocol):
    """Commits the session the ports write on."""

    async def commit(self) -> None: ...


@dataclass(frozen=True, kw_only=True)
class CoverReviewHoldDeps:
    """The run store, the rework store, the ledger, the session commit, the clock."""

    runs: AutopilotRunRepository
    recovery: RunRecoveryStore
    notices: NoticeLogStore
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
        if is_time_reply(run.notice_log.pending):
            await self._deps.notices.save(
                SaveNoticeLog(
                    run_id=run.run_id,
                    log=set_pending(run.notice_log, None),
                    base=run.notice_log,
                )
            )
        await self._deps.checkpoint.commit()
        return run.run_id

    async def escalate(self, run_id: UUID, version: int | None) -> None:
        """Escalate the held run (slide 1 may show an unreviewed cover).

        ``version`` is the carousel's lock version now; the escalation wakes once
        the owner changes the carousel. Without it the hold stays, and the worker
        escalates it when it outlives its limit (it reads the version itself).
        """
        if version is None:
            return
        await self._deps.recovery.clear_rework(run_id)
        moved = await self._deps.runs.transition(
            TransitionCommand(
                run_id=run_id,
                expected=_S.REWORKING,
                new=_S.ESCALATED,
                reason=REASON_COVER_REVIEW_UNSAFE,
            )
        )
        if moved:
            await self._deps.recovery.mark_escalated(
                EscalationMark(run_id=run_id, version=version)
            )
        await self._deps.checkpoint.commit()

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

    async def reopened(self, project_id: str) -> None:
        """Send a reopened carousel's run back for a new review (time kept)."""
        run = await self._deps.runs.find_by_carousel(project_id)
        if run is None or run.state not in _REOPENABLE:
            return
        await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=run.state,
                new=_S.REWORKING,
                reason=REASON_COVER_REVIEW_REOPENED,
                updated_at=run.updated_at,
            )
        )
        await self._deps.checkpoint.commit()


__all__ = ["CoverReviewHold", "CoverReviewHoldDeps"]
