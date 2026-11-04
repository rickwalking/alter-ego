"""The daily scan's one re-sent escalation notice.

``CAROUSEL_RETRY_SHIPPED_AT`` is the end of the deploy that added the owner's
carousel Retry: an escalation event from then on is a notice that carried it.
``RENOTICE_KEY`` is the ledger marker that keeps a run to one re-sent notice, ever.
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
RENOTICE_STATES = frozenset({AutopilotRunState.ESCALATED, AutopilotRunState.FAILED})
RESOLVED_REASONS = frozenset({
    REASON_DAILY_RECOVERY,
    REASON_DEAD_DISCARD,
    REASON_DEAD_RETRY,
    REASON_OWNER_CANCELLED,
})
