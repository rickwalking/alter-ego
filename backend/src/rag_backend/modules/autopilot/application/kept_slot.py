"""Approve a reopened review whose run kept its scheduled time.

Pedro's decision (2026-11-02): a slide-1 change on a scheduled carousel drops
its approval and sends the run back for a new review, keeping
``scheduled_at``. Approving that review keeps the time:

- the time is still ahead: final review is approved first (at the tapped
  revision), then the run goes ``awaiting_owner -> scheduled`` at the kept
  time. A refused approve moves nothing, so the time stays kept; an approve
  whose schedule move then loses (a double tap) leaves an approved carousel
  whose kept time the due sweep honours;
- the time has passed: the missed slot follows the scheduler's rule and
  expires (``schedule_withdrawn``), nothing is approved or published.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.application.owner_replies import OwnerReplies
from rag_backend.modules.autopilot.application.review_revision_guard import (
    TappedReview,
)
from rag_backend.modules.autopilot.application.schedule_picker import scheduled_text
from rag_backend.modules.autopilot.application.schedule_steps import (
    refusal_text,
    schedule_command,
)
from rag_backend.modules.autopilot.domain.gate import ResumeStatus
from rag_backend.modules.autopilot.domain.messages import review_keyboard
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository, Clock
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    scheduled_keyboard,
)
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.schedule_constants import (
    ANSWER_SCHEDULE_WITHDRAWN,
    ANSWER_SCHEDULED,
    REASON_SCHEDULE_WITHDRAWN,
    TEXT_KEPT_SLOT_REASON,
    TEXT_SCHEDULE_WITHDRAWN,
)
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    TEXT_ALREADY,
    TEXT_APPROVE_FAILED,
)

_S = AutopilotRunState


class KeptSlotDeps(Protocol):
    """The run store, the final-review approve and the clock (the publish
    choice's dependencies)."""

    @property
    def runs(self) -> AutopilotRunRepository: ...

    @property
    def approval(self) -> FinalReviewApproval: ...

    @property
    def clock(self) -> Clock: ...


class KeptSlotApproval:
    """The Approve tap on a reopened run that kept its scheduled time."""

    def __init__(self, deps: KeptSlotDeps, replies: OwnerReplies) -> None:
        self._deps = deps
        self._replies = replies

    async def approve(self, update: WebhookUpdate, tapped: TappedReview) -> None:
        """Schedule again at the kept time, or expire a time that passed."""
        run = tapped.run
        at = run.scheduled_at if run is not None else None
        if run is None or at is None:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        if at <= self._deps.clock.now():
            await self._expire(update, run)
            return
        status = await self._deps.approval.approve(run, tapped.revision)
        if status is not ResumeStatus.APPLIED:
            await self._refused(update, run, status)
            return
        await self._schedule(update, run, at)

    async def _expire(self, update: WebhookUpdate, run: AutopilotRun) -> None:
        moved = await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=_S.AWAITING_OWNER,
                new=_S.EXPIRED,
                reason=REASON_SCHEDULE_WITHDRAWN,
            )
        )
        if not moved:
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._replies.finish(
            update, ANSWER_SCHEDULE_WITHDRAWN, TEXT_SCHEDULE_WITHDRAWN
        )

    async def _refused(
        self, update: WebhookUpdate, run: AutopilotRun, status: ResumeStatus
    ) -> None:
        """Nothing moved: the review stays open with its time kept."""
        await self._replies.answer(update, TEXT_APPROVE_FAILED)
        await self._replies.edit(
            update, refusal_text(status), review_keyboard(run.run_id)
        )

    async def _schedule(
        self, update: WebhookUpdate, run: AutopilotRun, at: datetime
    ) -> None:
        if not await self._deps.runs.transition(schedule_command(run.run_id, at)):
            await self._replies.finish(update, ANSWER_ALREADY, TEXT_ALREADY)
            return
        await self._replies.answer(update, ANSWER_SCHEDULED)
        await self._replies.edit(
            update,
            scheduled_text(at, TEXT_KEPT_SLOT_REASON),
            scheduled_keyboard(run.run_id),
        )


__all__ = ["KeptSlotApproval", "KeptSlotDeps"]
