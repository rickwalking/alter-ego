"""Refuse a Telegram approve, publish or schedule tap for an outdated review.

The tapped message's revision (``tapped_revision``) must be the revision an
approve would answer now (``FinalReviewApproval.current_revision``). When it is
not, nothing is approved and nothing moves toward publishing, and the answer
says which way to go:

- no review was sent yet for the current revision (slide 1 changed on the
  website, the new review not queued): the run goes ``awaiting_owner ->
  reworking`` with its 72-hour anchor kept, and the worker's final-review stop
  sends it (``resending``);
- the current review could not be delivered (its attempts are exhausted): no
  bounce, the owner is pointed at the dashboard (``website``);
- otherwise a newer review is already in the chat (``replaced``).

A carousel rejected since the review was sent (the stuck-workflow sweep or the
abandoned-escalation settle; both bump the lock version, so every older tap is
outdated) has nothing left to review: the run closes ``awaiting_owner ->
rejected`` with the recovery's own ``carousel_rejected`` reason, instead of
going to ``reworking``, where nothing would ever close it (``rejected``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.cover_constants import (
    REASON_REVIEW_OUTDATED,
    TEXT_REVIEW_ON_WEBSITE,
    TEXT_REVIEW_REPLACED,
    TEXT_REVIEW_RESENDING,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.notice_log import (
    attempt_count,
    is_review_complete,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository
from rag_backend.modules.autopilot.notify_constants import (
    ATTEMPT_REVIEW_PREFIX,
    NOTIFY_MAX_ATTEMPTS,
)
from rag_backend.modules.autopilot.recovery_constants import REASON_CAROUSEL_REJECTED
from rag_backend.modules.autopilot.webhook_constants import TEXT_REJECTED

_S = AutopilotRunState


class OutdatedTap(StrEnum):
    """How an outdated tap is answered (``CURRENT``: not outdated)."""

    CURRENT = "current"
    REPLACED = "replaced"
    RESENDING = "resending"
    WEBSITE = "website"
    REJECTED = "rejected"


TEXT_BY_OUTDATED: dict[OutdatedTap, str] = {
    OutdatedTap.REPLACED: TEXT_REVIEW_REPLACED,
    OutdatedTap.RESENDING: TEXT_REVIEW_RESENDING,
    OutdatedTap.WEBSITE: TEXT_REVIEW_ON_WEBSITE,
    OutdatedTap.REJECTED: TEXT_REJECTED,
}


@dataclass(frozen=True, kw_only=True)
class TappedReview:
    """The run as the tap found it and the revision of the tapped message."""

    run: AutopilotRun | None
    revision: int | None


@dataclass(frozen=True, kw_only=True)
class RevisionGuard:
    """The approval that knows the current revision and the run store."""

    approval: FinalReviewApproval
    runs: AutopilotRunRepository

    async def check(self, tapped: TappedReview) -> OutdatedTap:
        """``CURRENT`` when the tap may act; otherwise how it was refused."""
        run = tapped.run
        if run is None or run.state is not _S.AWAITING_OWNER:
            return OutdatedTap.CURRENT
        current = await self.approval.current_revision(run)
        if current is None or current == tapped.revision:
            return OutdatedTap.CURRENT
        if await self.approval.carousel_rejected(run):
            await self.runs.transition(
                TransitionCommand.moving(run, _S.REJECTED, REASON_CAROUSEL_REJECTED)
            )
            return OutdatedTap.REJECTED
        return await self._outdated(run, current)

    async def _outdated(self, run: AutopilotRun, current: int) -> OutdatedTap:
        """Point at the newer review, the dashboard, or resend the review."""
        if is_review_complete(run.notice_log, current):
            return OutdatedTap.REPLACED
        key = f"{ATTEMPT_REVIEW_PREFIX}{current}"
        if attempt_count(run.notice_log, key) >= NOTIFY_MAX_ATTEMPTS:
            return OutdatedTap.WEBSITE
        await self.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=_S.AWAITING_OWNER,
                new=_S.REWORKING,
                reason=REASON_REVIEW_OUTDATED,
                updated_at=run.updated_at,
            )
        )
        return OutdatedTap.RESENDING


__all__ = ["TEXT_BY_OUTDATED", "OutdatedTap", "RevisionGuard", "TappedReview"]
