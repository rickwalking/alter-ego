"""Compare-and-set steps the owner webhook is allowed to request."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.recovery_constants import REASON_APPROVE_REFUSED
from rag_backend.modules.autopilot.webhook_constants import (
    REASON_APPROVE_FAILED,
    REASON_OWNER_APPROVED,
    REASON_OWNER_AUTOFIX,
    REASON_OWNER_REJECTED,
    REASON_OWNER_RETRY,
    REASON_OWNER_REWORK,
)

_AWAITING = AutopilotRunState.AWAITING_OWNER
_PUBLISHING = AutopilotRunState.PUBLISHING
_REJECTED = AutopilotRunState.REJECTED
_REWORKING = AutopilotRunState.REWORKING
_PUBLISH_FAILED = AutopilotRunState.PUBLISH_FAILED


@dataclass(frozen=True, kw_only=True)
class OwnerStep:
    """One compare-and-set this use case is allowed to request."""

    expected: AutopilotRunState
    new: AutopilotRunState
    reason: str


APPROVE_STEP = OwnerStep(
    expected=_AWAITING,
    new=_PUBLISHING,
    reason=REASON_OWNER_APPROVED,
)
APPROVE_FAILED_STEP = OwnerStep(
    expected=_PUBLISHING,
    new=_PUBLISH_FAILED,
    reason=REASON_APPROVE_FAILED,
)
REJECT_STEP = OwnerStep(
    expected=_AWAITING,
    new=_REJECTED,
    reason=REASON_OWNER_REJECTED,
)
RETRY_STEP = OwnerStep(
    expected=_PUBLISH_FAILED,
    new=_PUBLISHING,
    reason=REASON_OWNER_RETRY,
)
REWORK_STEP = OwnerStep(
    expected=_AWAITING,
    new=_REWORKING,
    reason=REASON_OWNER_REWORK,
)
# The editorial approve refused the owner's Approve: the review stays open.
APPROVE_REFUSED_STEP = OwnerStep(
    expected=_PUBLISHING,
    new=_AWAITING,
    reason=REASON_APPROVE_REFUSED,
)
# AE-0367: "Fix issues" queues a deterministic repair for the worker tick.
AUTOFIX_STEP = OwnerStep(
    expected=_AWAITING,
    new=_REWORKING,
    reason=REASON_OWNER_AUTOFIX,
)
