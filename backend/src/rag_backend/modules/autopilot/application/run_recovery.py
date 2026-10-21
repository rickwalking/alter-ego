"""Run recovery steps the runner performs before its one-run step.

* Expiry: ``awaiting_owner`` for 72 hours becomes ``expired`` (spec §3/§4).
* Wake: an ``escalated`` run whose carousel is back at final review becomes
  ``awaiting_owner`` again and the owner is re-notified (spec §4). The scan
  rotates by last check time, so old escalations never starve newer ones.
* Close: an ``escalated`` run whose carousel was rejected (web UI or the
  stuck auto-reject), or that nobody fixed within 72 hours, becomes
  ``rejected`` and the owner is told (QA r2 R1). The wake check runs first,
  and a carousel back at final review at a new lock version is never closed.
  Without a notifier such a run is first recorded as ``notifier_unconfigured``
  (which restarts its 72 hours); only then may it close (QA r3 Q3).
* Containment: an engine error the driver did not classify ends the run
  with a reason instead of rolling back the whole worker tick forever.

``_CONTAINED`` maps the state a run was in to where an unclassified engine
error leaves it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import structlog

from rag_backend.modules.autopilot.constants import (
    GATE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING,
)
from rag_backend.modules.autopilot.domain.gate import (
    EditorialDriver,
    GateSnapshot,
    OwnerReadyNotice,
    OwnerReadyNotifier,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.notice_log import is_review_complete
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository, Clock
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.recovery import (
    EscalatedScan,
    EscalationMark,
    RunRecoveryStore,
    UnnotifiedMark,
    WakeCheck,
)
from rag_backend.modules.autopilot.notify_constants import (
    REASON_NOTIFIER_UNCONFIGURED,
)
from rag_backend.modules.autopilot.pov_constants import REASON_THESIS_EXPIRED
from rag_backend.modules.autopilot.recovery_constants import (
    ENGINE_ERROR_DETAIL_MAX_CHARS,
    ESCALATED_SCAN_LIMIT,
    EXPIRY_SCAN_LIMIT,
    LOG_RUNNER_ENGINE_ERROR,
    LOG_RUNNER_WAKE_FAILED,
    OWNER_REVIEW_EXPIRY_HOURS,
    REASON_CAROUSEL_REJECTED,
    REASON_ENGINE_ERROR,
    REASON_ENGINE_ERROR_FORMAT,
    REASON_ESCALATION_EXPIRED,
    REASON_OWNER_EXPIRED,
    REASON_OWNER_FIXED,
    REASON_REVIEW_REOPENED,
)
from rag_backend.modules.editorial.public import PHASE_STATUS_REJECTED

logger = structlog.get_logger()

_S = AutopilotRunState
_CONTAINED: dict[AutopilotRunState, AutopilotRunState] = {
    _S.QUEUED: _S.FAILED,
    _S.GENERATING: _S.ESCALATED,
    _S.REWORKING: _S.ESCALATED,
}


@dataclass(frozen=True, kw_only=True)
class RecoveryDependencies:
    """Ports shared with the runner for one worker tick."""

    runs: AutopilotRunRepository
    editorial: EditorialDriver
    notices: OwnerReadyNotifier
    recovery: RunRecoveryStore
    clock: Clock
    notifier_configured: bool


class RunRecovery:
    """Expiry, escalation wake, and engine-error containment."""

    def __init__(self, deps: RecoveryDependencies) -> None:
        self._deps = deps

    async def sweep(self) -> int:
        """Expire stale reviews, close or wake escalations. Returns moves."""
        expired = await self._expire_due()
        expired += await self._expire_state(_S.AWAITING_THESIS, REASON_THESIS_EXPIRED)
        woken = await self._check_escalated()
        return expired + woken + await self._close_abandoned()

    async def contain(self, run: AutopilotRun, exc: BaseException) -> int:
        """Roll back, then end the run with an ``engine_error`` reason."""
        await self._deps.recovery.rollback()
        logger.exception(
            LOG_RUNNER_ENGINE_ERROR,
            run_id=str(run.run_id),
            error=type(exc).__name__,
            exc_info=exc,
        )
        current = await self._deps.runs.get(run.run_id)
        if current is None:
            return 1
        target = _CONTAINED.get(current.state)
        if target is None:
            return 1
        await self._end(current, target, engine_error_reason(exc))
        return 1

    async def mark(self, run: AutopilotRun, version: int) -> None:
        """Record the lock version an escalation happened at."""
        await self._deps.recovery.mark_escalated(
            EscalationMark(run_id=run.run_id, version=version)
        )

    async def _end(
        self,
        run: AutopilotRun,
        target: AutopilotRunState,
        reason: str,
    ) -> None:
        moved = await self._move(run, target, reason)
        if not moved or target is not _S.ESCALATED:
            return
        await self._deps.recovery.clear_rework(run.run_id)
        version = await self._version(run)
        if version is not None:
            await self.mark(run, version)

    async def _version(self, run: AutopilotRun) -> int | None:
        if run.carousel_project_id is None:
            return None
        try:
            snapshot = await self._deps.editorial.read_gate(run.carousel_project_id)
        except Exception:
            return None
        return snapshot.lock_version

    async def _expire_due(self) -> int:
        return await self._expire_state(_S.AWAITING_OWNER, REASON_OWNER_EXPIRED)

    async def _expire_state(self, state: AutopilotRunState, reason: str) -> int:
        """Runs left in ``state`` past the 72-hour window become ``expired``.

        An unanswered POV thesis expires like an unanswered review.
        """
        query = RunListQuery(state=state, limit=EXPIRY_SCAN_LIMIT)
        cutoff = self._deps.clock.now() - timedelta(hours=OWNER_REVIEW_EXPIRY_HOURS)
        moved = 0
        for run in await self._deps.runs.list_by_state(query):
            if run.updated_at is None or run.updated_at > cutoff:
                continue
            if await self._move(run, _S.EXPIRED, reason):
                moved += 1
        return moved

    async def _close_abandoned(self) -> int:
        """Escalations nobody fixed within the expiry window become rejected."""
        query = RunListQuery(state=_S.ESCALATED, limit=EXPIRY_SCAN_LIMIT)
        cutoff = self._deps.clock.now() - timedelta(hours=OWNER_REVIEW_EXPIRY_HOURS)
        moved = 0
        for run in await self._deps.runs.list_by_state(query):
            if run.updated_at is None or run.updated_at > cutoff:
                continue
            moved += await self._close_one(run)
        return moved

    async def _close_one(self, run: AutopilotRun) -> int:
        """Close an abandoned escalation unless its carousel was fixed."""
        if await self._keeps_open(run):
            return 0
        return int(await self._move(run, _S.REJECTED, REASON_ESCALATION_EXPIRED))

    async def _keeps_open(self, run: AutopilotRun) -> bool:
        if run.carousel_project_id is None:
            return False
        try:
            snapshot = await self._deps.editorial.read_gate(run.carousel_project_id)
        except Exception:
            logger.exception(LOG_RUNNER_WAKE_FAILED, run_id=str(run.run_id))
            return True
        if not _fixed_at_new_version(run, snapshot):
            return False
        return not await self._may_close(run)

    async def _may_close(self, run: AutopilotRun) -> bool:
        """A fixed run closes only once recorded as ``notifier_unconfigured``."""
        if self._deps.notifier_configured:
            return False
        if run.state_reason == REASON_NOTIFIER_UNCONFIGURED:
            return True
        now = self._deps.clock.now()
        await self._deps.recovery.mark_unnotified(
            UnnotifiedMark(run_id=run.run_id, at=now)
        )
        return False

    async def _check_escalated(self) -> int:
        scan = EscalatedScan(limit=ESCALATED_SCAN_LIMIT)
        moved = 0
        for run in await self._deps.recovery.escalated_for_check(scan):
            now = self._deps.clock.now()
            await self._deps.recovery.mark_checked(WakeCheck(run_id=run.run_id, at=now))
            moved += await self._check_one(run)
        return moved

    async def _check_one(self, run: AutopilotRun) -> int:
        project_id = run.carousel_project_id
        if project_id is None:
            return 0
        try:
            snapshot = await self._deps.editorial.read_gate(project_id)
        except Exception:
            logger.exception(LOG_RUNNER_WAKE_FAILED, run_id=str(run.run_id))
            return 0
        if snapshot.phase_status == PHASE_STATUS_REJECTED:
            return int(await self._move(run, _S.REJECTED, REASON_CAROUSEL_REJECTED))
        return await self._wake(run, snapshot, project_id)

    async def _wake(
        self,
        run: AutopilotRun,
        snapshot: GateSnapshot,
        project_id: str,
    ) -> int:
        if not self._deps.notifier_configured:
            return 0
        if not _back_at_final_review(run, snapshot):
            return 0
        return await self._reopen(run, snapshot, project_id)

    async def _reopen(
        self,
        run: AutopilotRun,
        snapshot: GateSnapshot,
        project_id: str,
    ) -> int:
        reviewed = is_review_complete(run.notice_log, snapshot.lock_version)
        reason = REASON_REVIEW_REOPENED if reviewed else REASON_OWNER_FIXED
        if not await self._move(run, _S.AWAITING_OWNER, reason):
            return 0
        if not reviewed:
            await self._deps.notices.notify_ready(_notice(run, snapshot, project_id))
        return 1

    async def _move(
        self,
        run: AutopilotRun,
        new: AutopilotRunState,
        reason: str,
    ) -> bool:
        return await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=run.state,
                new=new,
                reason=reason,
            )
        )


def engine_error_reason(exc: BaseException) -> str:
    """``engine_error:<type>:<message>``, bounded for the Telegram notice."""
    reason = REASON_ENGINE_ERROR_FORMAT.format(
        prefix=REASON_ENGINE_ERROR,
        kind=type(exc).__name__,
        detail=str(exc),
    )
    return reason[:ENGINE_ERROR_DETAIL_MAX_CHARS]


def _at_final_review(snapshot: GateSnapshot) -> bool:
    if snapshot.stale or snapshot.phase != GATE_FINAL_REVIEW:
        return False
    return snapshot.phase_status == PHASE_STATUS_AWAITING


def _fixed_at_new_version(run: AutopilotRun, snapshot: GateSnapshot) -> bool:
    """The owner changed the carousel and it waits at final review again."""
    if not _at_final_review(snapshot):
        return False
    return run.escalated_version != snapshot.lock_version


def _back_at_final_review(run: AutopilotRun, snapshot: GateSnapshot) -> bool:
    if not _at_final_review(snapshot):
        return False
    if run.state_reason == REASON_NOTIFIER_UNCONFIGURED:
        return True
    return run.escalated_version != snapshot.lock_version


def _notice(
    run: AutopilotRun,
    snapshot: GateSnapshot,
    project_id: str,
) -> OwnerReadyNotice:
    return OwnerReadyNotice(
        run_id=run.run_id,
        project_id=project_id,
        revision=snapshot.lock_version,
        persona_score=snapshot.persona_score,
        sources_count=len(snapshot.sources),
    )
