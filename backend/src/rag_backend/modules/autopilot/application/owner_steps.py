"""Compare-and-set steps the owner webhook is allowed to request."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.constants import REASON_REVISION_CAP
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.webhook_constants import (
    REASON_APPROVE_FAILED,
    REASON_OWNER_APPROVED,
    REASON_OWNER_REJECTED,
    REASON_OWNER_RETRY,
    REASON_OWNER_REWORK,
)

_AWAITING = AutopilotRunState.AWAITING_OWNER
_PUBLISHING = AutopilotRunState.PUBLISHING
_REJECTED = AutopilotRunState.REJECTED
_REWORKING = AutopilotRunState.REWORKING
_ESCALATED = AutopilotRunState.ESCALATED
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
CAP_STEP = OwnerStep(
    expected=_REWORKING,
    new=_ESCALATED,
    reason=REASON_REVISION_CAP,
)
