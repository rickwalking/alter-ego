"""Find the stuck runs and stage their one re-sent escalation notice.

Staging writes the outbox row and the ledger marker in one transaction, under the
run's row lock, so a run gets one event however many scans race. The worker's
notifier delivers the event. Neither the run's state nor ``updated_at`` moves.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.events.outbox_dispatch import build_event_records
from rag_backend.modules.autopilot.constants import (
    AGGREGATE_TYPE_AUTOPILOT_RUN,
    EVENT_TYPE_PUBLISH_NOTICE,
    EVENT_TYPE_STATE_CHANGED,
)
from rag_backend.modules.autopilot.domain.escalation_renotice import (
    PastNotice,
    carried_retry,
    mark_renoticed,
    renotice_due,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun
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
_RETRY_EVENT_TYPES = (EVENT_TYPE_STATE_CHANGED, EVENT_TYPE_PUBLISH_NOTICE)

CarouselOpen = Callable[[AsyncSession, str], Awaitable[bool]]
"""Whether the carousel can still be retried, read on the staging transaction."""


class SqlEscalationRenotices:
    """Session-scoped. ``stage`` leaves the commit to the caller."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def unsent(self) -> list[AutopilotRun]:
        """Due runs that never got a notice with a Retry."""
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
        notified = await self._had_retry_notice(runs)
        return [run for run in runs if str(run.run_id) not in notified]

    async def stage(self, run_id: UUID, carousel_open: CarouselOpen) -> bool:
        """Stage the event and the marker; False when the run is no longer eligible.

        Every listing check runs again under the row lock, ``carousel_open`` on the
        same transaction: a run can change between the listing and this call.
        """
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
        if not await self._still_eligible(run, carousel_open):
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

    async def _still_eligible(
        self, run: AutopilotRun, carousel_open: CarouselOpen
    ) -> bool:
        if not renotice_due(run) or await self._had_retry_notice([run]):
            return False
        return await carousel_open(self._session, run.carousel_project_id or "")

    async def _had_retry_notice(self, runs: list[AutopilotRun]) -> set[str]:
        """Runs with an event whose notice offered a Retry, delivered or not."""
        result = await self._session.execute(
            select(
                _E.aggregate_id,
                _E.event_type,
                _E.payload,
                (_E.created_at >= CAROUSEL_RETRY_SHIPPED_AT).label("since_retry"),
            ).where(
                _E.aggregate_type == AGGREGATE_TYPE_AUTOPILOT_RUN,
                _E.event_type.in_(_RETRY_EVENT_TYPES),
                _E.aggregate_id.in_([str(run.run_id) for run in runs]),
            )
        )
        return {
            run_id
            for run_id, event_type, payload, since_retry in result.tuples().all()
            if carried_retry(
                PastNotice(
                    run_id=UUID(run_id),
                    event_type=event_type,
                    payload=_mapping(cast(object, payload)),
                    since_retry=bool(since_retry),
                )
            )
        }


def _mapping(payload: object) -> Mapping[str, object]:
    return cast(dict[str, object], payload) if isinstance(payload, dict) else {}


__all__ = ["CarouselOpen", "SqlEscalationRenotices"]
