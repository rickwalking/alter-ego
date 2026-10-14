"""Apply an owner rework the webhook queued (AE-0348 QA round 1, H4).

The webhook only records phase and feedback and answers Telegram at once.
The runner calls ``apply`` on the worker tick, where the LLM regeneration
has no ~100 s Cloudflare cap.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.application.run_recovery import RunRecovery
from rag_backend.modules.autopilot.constants import (
    GATE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING,
    REASON_PROJECT_MISSING,
    REASON_REVISION_CAP,
)
from rag_backend.modules.autopilot.domain.gate import (
    EditorialDriver,
    GateSnapshot,
    ResumeCommand,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository
from rag_backend.modules.autopilot.domain.recovery import RunRecoveryStore
from rag_backend.modules.autopilot.recovery_constants import REASON_REWORK_RETRY
from rag_backend.modules.editorial.public import REVIEW_ACTION_REVISE


@dataclass(frozen=True, kw_only=True)
class ReworkDependencies:
    """Ports the rework step shares with the runner."""

    runs: AutopilotRunRepository
    editorial: EditorialDriver
    recovery: RunRecoveryStore
    escalations: RunRecovery


class ReworkStep:
    """One queued rework: revise final review toward the owner's phase."""

    def __init__(self, deps: ReworkDependencies) -> None:
        self._deps = deps

    async def try_apply(self, run: AutopilotRun) -> int | None:
        """Revise once, or None when there is no rework to apply.

        A queued rework whose workflow already left final review was applied
        by an earlier tick that failed before it cleared the intent; it is
        dropped and the caller drives the run as usual.
        """
        if run.rework_phase is None:
            return None
        project_id = run.carousel_project_id
        if project_id is None:
            await self._end(run, AutopilotRunState.ESCALATED, REASON_PROJECT_MISSING)
            return 1
        snapshot = await self._deps.editorial.read_gate(project_id)
        if not _at_final_review(snapshot):
            await self._deps.recovery.clear_rework(run.run_id)
            return None
        return await self._apply(run, snapshot, project_id)

    async def _apply(
        self,
        run: AutopilotRun,
        snapshot: GateSnapshot,
        project_id: str,
    ) -> int:
        result = await self._deps.editorial.resume(_revise(run, snapshot, project_id))
        if result.status is ResumeStatus.APPLIED:
            await self._deps.recovery.clear_rework(run.run_id)
            return 1
        if result.status is ResumeStatus.REVISION_CAP:
            await self._cap(run, project_id)
            return 1
        await self._end(run, AutopilotRunState.AWAITING_OWNER, REASON_REWORK_RETRY)
        return 1

    async def _cap(self, run: AutopilotRun, project_id: str) -> None:
        moved = await self._end(run, AutopilotRunState.ESCALATED, REASON_REVISION_CAP)
        if not moved:
            return
        after = await self._deps.editorial.read_gate(project_id)
        await self._deps.escalations.mark(run, after.lock_version)

    async def _end(
        self,
        run: AutopilotRun,
        new: AutopilotRunState,
        reason: str,
    ) -> bool:
        await self._deps.recovery.clear_rework(run.run_id)
        return await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=run.state,
                new=new,
                reason=reason,
            )
        )


def _at_final_review(snapshot: GateSnapshot) -> bool:
    return (
        snapshot.phase == GATE_FINAL_REVIEW
        and snapshot.phase_status == PHASE_STATUS_AWAITING
    )


def _revise(
    run: AutopilotRun,
    snapshot: GateSnapshot,
    project_id: str,
) -> ResumeCommand:
    return ResumeCommand(
        project_id=project_id,
        action=REVIEW_ACTION_REVISE,
        expected_version=snapshot.lock_version,
        feedback=run.rework_feedback or "",
        phase=GATE_FINAL_REVIEW,
        target_phase=run.rework_phase or "",
    )
