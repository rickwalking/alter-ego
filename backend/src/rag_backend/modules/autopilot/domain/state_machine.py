"""Allowed autopilot run transitions (architecture §4).

The table is the spec. Persistence enforces it with a compare-and-set;
this module only answers whether the requested pair is legal.

Beyond the architecture table, ``(queued, failed)`` covers three provider failures on
start, and ``(publishing, awaiting_owner)`` covers the editorial approve refusing the
owner's Approve, so the review stays open instead of a dead ``publish_failed``. A POV
run waits in ``awaiting_thesis`` for the owner's thesis before generating. ``scheduled``
holds the owner's publish time: cancel reopens the review, a carousel no longer approved
at the due time expires the run, and the owner may move a scheduled run to another day
or time.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.domain.exceptions import InvalidAutopilotTransition
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionPair,
)

_S = AutopilotRunState

ALLOWED_TRANSITIONS: frozenset[tuple[AutopilotRunState, AutopilotRunState]] = (
    frozenset({
        (_S.QUEUED, _S.GENERATING),
        (_S.QUEUED, _S.FAILED),
        (_S.GENERATING, _S.AWAITING_OWNER),
        (_S.GENERATING, _S.ESCALATED),
        (_S.GENERATING, _S.FAILED),
        (_S.AWAITING_OWNER, _S.PUBLISHING),
        (_S.AWAITING_OWNER, _S.REWORKING),
        (_S.AWAITING_OWNER, _S.REJECTED),
        (_S.AWAITING_OWNER, _S.EXPIRED),
        (_S.REWORKING, _S.AWAITING_OWNER),
        (_S.REWORKING, _S.ESCALATED),
        (_S.ESCALATED, _S.AWAITING_OWNER),
        (_S.ESCALATED, _S.REJECTED),
        (_S.PUBLISHING, _S.PUBLISHED),
        (_S.PUBLISHING, _S.PUBLISH_FAILED),
        (_S.PUBLISHING, _S.AWAITING_OWNER),
        (_S.PUBLISH_FAILED, _S.PUBLISHING),
        (_S.QUEUED, _S.AWAITING_THESIS),
        (_S.AWAITING_THESIS, _S.QUEUED),
        (_S.AWAITING_THESIS, _S.REJECTED),
        (_S.AWAITING_THESIS, _S.EXPIRED),
        (_S.AWAITING_OWNER, _S.SCHEDULED),
        (_S.SCHEDULED, _S.PUBLISHING),
        (_S.SCHEDULED, _S.AWAITING_OWNER),
        (_S.SCHEDULED, _S.EXPIRED),
        (_S.SCHEDULED, _S.SCHEDULED),
    })
)


def assert_allowed(pair: TransitionPair) -> None:
    """Raise ``InvalidAutopilotTransition`` when ``pair`` is not in the table."""
    if (pair.expected, pair.new) not in ALLOWED_TRANSITIONS:
        raise InvalidAutopilotTransition(pair)
