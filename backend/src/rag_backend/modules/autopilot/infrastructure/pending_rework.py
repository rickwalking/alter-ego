"""Pending rework phase, stored on the run's notice ledger.

Keyed by the owner chat id. A rework phase is only visible on a run still
``awaiting_owner``, so a later approve or reject cannot be undone by a stale
text message. An edited POV thesis ("Editar") is pending on a run
``awaiting_thesis``; ``take`` used to scan only ``awaiting_owner`` runs, so the
owner's typed thesis was dropped silently.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
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
from rag_backend.modules.autopilot.pov_constants import THESIS_PENDING_PHASE
from rag_backend.modules.autopilot.webhook_constants import REWORK_SCAN_LIMIT

_THESIS_STATE = AutopilotRunState.AWAITING_THESIS
_REWORK_STATE = AutopilotRunState.AWAITING_OWNER
_SCANNED_STATES = (_REWORK_STATE, _THESIS_STATE)


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
        for state in _SCANNED_STATES:
            for run in await self._runs.list_by_state(
                RunListQuery(state=state, limit=REWORK_SCAN_LIMIT)
            ):
                found = _match(run, owner_chat_id)
                if found is not None:
                    return await self._clear(run, found)
        return None

    async def _clear(self, run: AutopilotRun, found: StoredPending) -> PendingRework:
        cleared = set_pending(run.notice_log, None)
        await self._notices.save(SaveNoticeLog(run_id=run.run_id, log=cleared))
        return PendingRework(
            owner_chat_id=found.owner_chat_id,
            run_id=run.run_id,
            phase=found.phase,
        )


def _match(run: AutopilotRun, owner_chat_id: str) -> StoredPending | None:
    """The owner's pending reply on ``run``, when it belongs to the run's state."""
    pending = run.notice_log.pending
    if pending is None or pending.owner_chat_id != owner_chat_id:
        return None
    expected = _THESIS_STATE if pending.phase == THESIS_PENDING_PHASE else _REWORK_STATE
    return pending if run.state is expected else None
