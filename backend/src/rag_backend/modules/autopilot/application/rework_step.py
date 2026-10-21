"""Apply an owner rework the webhook queued.

The webhook only records phase and feedback and answers Telegram at once.
The runner calls ``apply`` on the worker tick, where the LLM regeneration
has no ~100 s Cloudflare cap.

A "Fix issues" tap is queued the same way (phase marker
``AUTOFIX_REWORK_PHASE``). The tick runs the deterministic repair and
re-render, then hands the run to the normal final-review stop, which moves it
back to ``awaiting_owner`` and stages the fresh review (new lock version).
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
from rag_backend.modules.autopilot.cover_constants import (
    COVER_REWORK_PHASE,
    REASON_COVER_MISSING,
    REASON_COVER_RENDER_FAILED,
)
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixCommand,
    AutofixStatus,
    ContentAutofixer,
)
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverOffers,
    CoverSwitchCommand,
    CoverSwitcher,
    CoverSwitchStatus,
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
from rag_backend.modules.autopilot.webhook_constants import AUTOFIX_REWORK_PHASE
from rag_backend.modules.editorial.public import REVIEW_ACTION_REVISE


@dataclass(frozen=True, kw_only=True)
class ReworkDependencies:
    """Ports the rework step shares with the runner.

    ``covers`` / ``cover_switch`` are the owner's GrokBot cover choice and the
    slide-1 re-render.
    """

    runs: AutopilotRunRepository
    editorial: EditorialDriver
    recovery: RunRecoveryStore
    escalations: RunRecovery
    autofix: ContentAutofixer | None = None
    covers: CoverOffers | None = None
    cover_switch: CoverSwitcher | None = None


class ReworkStep:
    """One queued rework: revise final review toward the owner's phase."""

    def __init__(self, deps: ReworkDependencies) -> None:
        self._deps = deps

    async def try_apply(self, run: AutopilotRun) -> int | None:
        """Revise once, or None when there is no rework to apply.

        A queued rework whose workflow already left final review was applied
        by an earlier tick that failed before it cleared the intent; it is
        dropped and the caller drives the run as usual.

        "Fix issues" and "Usar capa do Grok" are special reworks, not a revise.
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
        special = {
            AUTOFIX_REWORK_PHASE: self._autofix,
            COVER_REWORK_PHASE: self._cover,
        }.get(run.rework_phase)
        if special is not None:
            return await special(run, snapshot, project_id)
        return await self._apply(run, snapshot, project_id)

    async def _autofix(
        self,
        run: AutopilotRun,
        snapshot: GateSnapshot,
        project_id: str,
    ) -> int | None:
        """Repair once; None hands the run to the final-review stop.

        A conflict keeps the intent for the next tick (fresh lock version).
        """
        autofix = self._deps.autofix
        if autofix is None:
            await self._end(run, AutopilotRunState.AWAITING_OWNER, REASON_REWORK_RETRY)
            return 1
        command = AutofixCommand(
            project_id=project_id, expected_version=snapshot.lock_version
        )
        outcome = await autofix.autofix(command)
        if outcome.status is AutofixStatus.CONFLICT:
            return 1
        await self._deps.recovery.clear_rework(run.run_id)
        return None

    async def _cover(
        self,
        run: AutopilotRun,
        snapshot: GateSnapshot,
        project_id: str,
    ) -> int | None:
        """Switch slide 1; None hands the run to the final-review stop.

        A conflict keeps the intent for the next tick; a cover whose file is
        gone sends the run back to the owner's review unchanged; a failed
        re-render is escalated (the owner is told), never reported as done.
        """
        switcher = self._deps.cover_switch
        covers = self._deps.covers
        if switcher is None or covers is None:
            await self._end(run, AutopilotRunState.AWAITING_OWNER, REASON_REWORK_RETRY)
            return 1
        command = CoverSwitchCommand(
            project_id=project_id,
            expected_version=snapshot.lock_version,
            cover=await covers.chosen_cover(run),
        )
        status = await switcher.switch(command)
        if status is CoverSwitchStatus.CONFLICT:
            return 1
        if status is CoverSwitchStatus.MISSING:
            await self._end(run, AutopilotRunState.AWAITING_OWNER, REASON_COVER_MISSING)
            return 1
        if status is CoverSwitchStatus.RENDER_FAILED:
            await self._escalate(run, project_id, REASON_COVER_RENDER_FAILED)
            return 1
        await self._deps.recovery.clear_rework(run.run_id)
        return None

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
        await self._escalate(run, project_id, REASON_REVISION_CAP)

    async def _escalate(self, run: AutopilotRun, project_id: str, reason: str) -> None:
        moved = await self._end(run, AutopilotRunState.ESCALATED, reason)
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
