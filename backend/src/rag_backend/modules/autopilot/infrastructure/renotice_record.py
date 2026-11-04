"""The outbox event of one re-sent escalation notice."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from rag_backend.infrastructure.events.outbox_dispatch import EventRecord
from rag_backend.modules.autopilot.constants import (
    AGGREGATE_TYPE_AUTOPILOT_RUN,
    EVENT_VERSION,
    METADATA_MODULE,
    MODULE_NAME,
)
from rag_backend.modules.autopilot.domain.escalation_renotice import renotice_payload
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.notify_constants import (
    EVENT_TYPE_ESCALATION_RENOTICE,
)


def renotice_record(run: AutopilotRun) -> EventRecord:
    """The event the notifier reads as an escalation notice for ``run``."""
    return EventRecord(
        event_id=str(uuid4()),
        event_type=EVENT_TYPE_ESCALATION_RENOTICE,
        aggregate_id=str(run.run_id),
        aggregate_type=AGGREGATE_TYPE_AUTOPILOT_RUN,
        version=EVENT_VERSION,
        payload=renotice_payload(run),
        metadata={METADATA_MODULE: MODULE_NAME},
        emitted_at=datetime.now(UTC),
    )


__all__ = ["renotice_record"]
