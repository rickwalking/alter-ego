"""The daily scan's one re-sent escalation notice.

``CAROUSEL_RETRY_SHIPPED_AT`` is the end of the deploy that added the owner's
carousel Retry: an escalation event from then on is a notice that carried it.
``RENOTICE_KEY`` starts the ledger marker of one queued notice, with its event id. A
new notice is queued only when every earlier one was given up on, undelivered.
``RENOTICE_SENDING_KEY`` starts the claim committed before a send: it stays unless
the send certainly did not happen, so a notice is never sent twice.
``RENOTICE_MAX_REQUEUES`` counts the notices queued after a run's first one.
"""

from datetime import UTC, datetime

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.queue_constants import (
    REASON_DAILY_RECOVERY,
    REASON_DEAD_DISCARD,
    REASON_DEAD_RETRY,
    REASON_OWNER_CANCELLED,
)

CAROUSEL_RETRY_SHIPPED_AT = datetime(2026, 11, 4, 9, 21, 21, tzinfo=UTC)
RENOTICE_KEY = "scan_renotified"
RENOTICE_SENDING_KEY = "scan_renotice_sending"
RENOTICE_KEY_FORMAT = "{key}:{event_id}"
RENOTICE_MAX_REQUEUES = 3
LOG_RENOTICE_CAP_HIT = "autopilot_renotice_cap_hit"
RENOTICE_STATES = frozenset({AutopilotRunState.ESCALATED, AutopilotRunState.FAILED})
RESOLVED_REASONS = frozenset({
    REASON_DAILY_RECOVERY,
    REASON_DEAD_DISCARD,
    REASON_DEAD_RETRY,
    REASON_OWNER_CANCELLED,
})
