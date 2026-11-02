"""Refuse a Telegram approve, publish or schedule tap for an outdated review.

The tapped message's revision (``tapped_revision``) must be the revision an
approve would answer now (``FinalReviewApproval.current_revision``). When it is
not, nothing is approved and nothing moves toward publishing. If no review was
sent yet for the current revision (slide 1 changed on the website, the new
review not delivered or never queued), the run goes ``awaiting_owner ->
reworking`` and the worker's final-review stop sends it; otherwise the newer
review is already on screen.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.cover_constants import REASON_REVIEW_OUTDATED
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.notice_log import is_review_complete
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository

_S = AutopilotRunState


async def refused_as_outdated(
    approval: FinalReviewApproval,
    runs: AutopilotRunRepository,
    target: tuple[AutopilotRun | None, int | None],
) -> bool:
    """True when the tap must change nothing; a missing review is requested."""
    run, revision = target
    if run is None or run.state is not _S.AWAITING_OWNER:
        return False
    current = await approval.current_revision(run)
    if current is None or current == revision:
        return False
    if not is_review_complete(run.notice_log, current):
        await runs.transition(
            TransitionCommand.moving(run, _S.REWORKING, REASON_REVIEW_OUTDATED)
        )
    return True


__all__ = ["refused_as_outdated"]
