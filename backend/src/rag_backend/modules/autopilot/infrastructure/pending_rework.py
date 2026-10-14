"""Pending rework phase, stored on the run's notice ledger.

Keyed by the owner chat id. Only runs still ``awaiting_owner`` are visible,
so a later approve or reject cannot be undone by a stale text message.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import (
    StoredPending,
    set_pending,
)
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog
from rag_backend.modules.autopilot.domain.owner_ports import PendingRework
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    NoticeLogStore,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.webhook_constants import REWORK_SCAN_LIMIT


class SqlPendingReworkStore:
    """Reads and writes the pending phase through the notice ledger."""

    def __init__(self, runs: AutopilotRunRepository, notices: NoticeLogStore) -> None:
        self._runs = runs
        self._notices = notices

    async def put(self, pending: PendingRework) -> None:
        """Remember this owner's phase on the run."""
        run = await self._runs.get(pending.run_id)
        if run is None:
            return
        stored = StoredPending(owner_chat_id=pending.owner_chat_id, phase=pending.phase)
        log = set_pending(run.notice_log, stored)
        await self._notices.save(SaveNoticeLog(run_id=run.run_id, log=log))

    async def take(self, owner_chat_id: str) -> PendingRework | None:
        """Return and clear the pending phase for this owner."""
        query = RunListQuery(
            state=AutopilotRunState.AWAITING_OWNER,
            limit=REWORK_SCAN_LIMIT,
        )
        runs = await self._runs.list_by_state(query)
        for run in runs:
            found = _match(run.notice_log.pending, owner_chat_id)
            if found is None:
                continue
            cleared = set_pending(run.notice_log, None)
            await self._notices.save(SaveNoticeLog(run_id=run.run_id, log=cleared))
            return PendingRework(
                owner_chat_id=owner_chat_id,
                run_id=run.run_id,
                phase=found.phase,
            )
        return None


def _match(pending: StoredPending | None, owner_chat_id: str) -> StoredPending | None:
    if pending is None or pending.owner_chat_id != owner_chat_id:
        return None
    return pending
