"""Find the stuck runs and stage their one re-sent escalation notice.

Staging writes the outbox row and the ledger marker in one transaction, under the
run's row lock, so a run gets one event however many scans race. The worker's
notifier delivers the event. Neither the run's state nor ``updated_at`` moves.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.events.outbox_dispatch import build_event_records
from rag_backend.modules.autopilot.constants import (
    AGGREGATE_TYPE_AUTOPILOT_RUN,
    EVENT_TYPE_STATE_CHANGED,
    PAYLOAD_STATE,
)
from rag_backend.modules.autopilot.domain.escalation_renotice import (
    mark_renoticed,
    renotice_due,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.notice_source import SqlNoticeLogStore
from rag_backend.modules.autopilot.infrastructure.renotice_record import (
    renotice_record,
)
from rag_backend.modules.autopilot.infrastructure.run_mapping import run_from_row
from rag_backend.modules.autopilot.renotice_constants import (
    CAROUSEL_RETRY_SHIPPED_AT,
    RENOTICE_STATES,
)

_R = AutopilotRunModel
_E = EventOutboxModel


class SqlEscalationRenotices:
    """Session-scoped. ``stage`` leaves the commit to the caller."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def unsent(self) -> list[AutopilotRun]:
        """Due runs that got no escalation notice since Retry shipped."""
        result = await self._session.execute(
            select(_R)
            .where(
                _R.state.in_([state.value for state in RENOTICE_STATES]),
                _R.carousel_project_id.is_not(None),
            )
            .order_by(_R.updated_at, _R.id)
        )
        due = [run_from_row(row) for row in result.scalars().all()]
        runs = [run for run in due if renotice_due(run)]
        notified = await self._escalated_since_retry(runs)
        return [run for run in runs if str(run.run_id) not in notified]

    async def stage(self, run_id: UUID) -> bool:
        """Stage the event and the marker; False when the run is no longer due."""
        result = await self._session.execute(
            select(_R)
            .where(_R.id == run_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        run = run_from_row(row)
        if not renotice_due(run):
            return False
        audit, outbox = build_event_records(renotice_record(run))
        self._session.add(audit)
        self._session.add(outbox)
        await self._session.flush()
        await SqlNoticeLogStore(self._session).save(
            SaveNoticeLog(
                run_id=run.run_id,
                log=mark_renoticed(run.notice_log),
                base=run.notice_log,
            )
        )
        return True

    async def _escalated_since_retry(self, runs: list[AutopilotRun]) -> set[str]:
        """Runs with an escalation event since Retry shipped, delivered or not."""
        result = await self._session.execute(
            select(_E.aggregate_id, _E.payload).where(
                _E.aggregate_type == AGGREGATE_TYPE_AUTOPILOT_RUN,
                _E.event_type == EVENT_TYPE_STATE_CHANGED,
                _E.aggregate_id.in_([str(run.run_id) for run in runs]),
                _E.created_at >= CAROUSEL_RETRY_SHIPPED_AT,
            )
        )
        return {
            cast(str, run_id)
            for run_id, payload in result.all()
            if _is_escalation(cast(object, payload))
        }


def _is_escalation(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    return payload.get(PAYLOAD_STATE) == AutopilotRunState.ESCALATED.value


__all__ = ["SqlEscalationRenotices"]
