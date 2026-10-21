"""Repair before revise at the content and design gates.

A gate that fails only on blocking presentation rules (sentence case, empty
body, EN equal to PT, item counts, tag balance) is first repaired with the
owner "Fix issues" plan through the editorial facade, then read again. A clean
gate is approved without spending a revision; whatever is left is revised
with feedback that names each failing slide.

A revise regenerates the whole phase: the engine has no per-slide regenerate
behind a review decision (structured feedback is final-review only). The
content phase still re-drafts each blocking slide once on its own.

With a model fixer wired (the autopilot worker), content-quality and
voice-score failures are not revised: ``SlideAutofixStep`` rewrites each
failing slide (3 attempts) and escalates what is left.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import structlog

from rag_backend.modules.autopilot.application.gate_read import GateRead
from rag_backend.modules.autopilot.application.slide_autofix import (
    SlideAutofixDependencies,
    SlideAutofixStep,
)
from rag_backend.modules.autopilot.constants import REASON_DESIGN
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixStatus,
    GateRepairCommand,
    GateRepairer,
    GateRepairOutcome,
    SlideFixer,
)
from rag_backend.modules.autopilot.domain.gate import EditorialDriver, GateAction
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.quality_constants import (
    LOG_CONTENT_AUTOREPAIRED,
    LOG_FIELD_FIXED_RULES,
    LOG_FIELD_NEXT_ACTION,
    LOG_FIELD_REMAINING_RULES,
    LOG_GATE_REPAIR_CONFLICT,
    LOG_GATE_REPAIR_NOOP,
    QUALITY_GATES,
    REASON_CONTENT_QUALITY,
)

logger = structlog.get_logger()

_REPAIRABLE_REASONS: frozenset[str] = frozenset({REASON_CONTENT_QUALITY, REASON_DESIGN})
_FAILED_ACTIONS: frozenset[GateAction] = frozenset({
    GateAction.REVISE,
    GateAction.ESCALATE,
})


@dataclass(frozen=True, kw_only=True)
class GateRepairDependencies:
    """The driver to read the gate again, the repairer and the model fixer.

    ``fixer`` is the model fix for the slides the repair could not fix.
    """

    editorial: EditorialDriver
    repairer: GateRepairer | None = None
    fixer: SlideFixer | None = None


def _repairable(read: GateRead) -> bool:
    return (
        read.decision.action in _FAILED_ACTIONS
        and read.decision.reason in _REPAIRABLE_REASONS
        and read.snapshot.phase in QUALITY_GATES
    )


class GateRepairStep:
    """At most one deterministic repair per tick, before a revise or escalation."""

    def __init__(self, deps: GateRepairDependencies) -> None:
        self._deps = deps
        self._autofix = SlideAutofixStep(
            SlideAutofixDependencies(editorial=deps.editorial, fixer=deps.fixer)
        )

    async def apply(self, read: GateRead) -> GateRead | None:
        """The gate to act on; None when a write lost the lock (next tick).

        The deterministic repair first, then the model fix of what
        is still failing; each step returns its input unchanged when it does
        not apply.
        """
        repaired = await self._repair(read)
        return await self._autofix.apply(repaired) if repaired is not None else None

    async def _repair(self, read: GateRead) -> GateRead | None:
        repairer = self._deps.repairer
        if repairer is None or not _repairable(read):
            return read
        outcome = await repairer.repair_gate(_command(read))
        if outcome.status is AutofixStatus.CONFLICT:
            _log(LOG_GATE_REPAIR_CONFLICT, read)
            return None
        if outcome.status is not AutofixStatus.FIXED:
            _log(LOG_GATE_REPAIR_NOOP, read)
            return read
        return await self._reread(read, outcome)

    async def _reread(self, read: GateRead, outcome: GateRepairOutcome) -> GateRead:
        project_id = read.run.carousel_project_id or ""
        snapshot = await self._deps.editorial.read_gate(project_id)
        fresh = GateRead(run=read.run, snapshot=snapshot, decision=decide(snapshot))
        _log(
            LOG_CONTENT_AUTOREPAIRED,
            read,
            {
                LOG_FIELD_FIXED_RULES: list(outcome.fixed_rules),
                LOG_FIELD_REMAINING_RULES: list(outcome.remaining_rules),
                LOG_FIELD_NEXT_ACTION: fresh.decision.action.value,
            },
        )
        return fresh


def _command(read: GateRead) -> GateRepairCommand:
    return GateRepairCommand(
        project_id=read.run.carousel_project_id or "",
        expected_version=read.snapshot.lock_version,
        phase=read.snapshot.phase,
    )


def _log(event: str, read: GateRead, extra: Mapping[str, object] | None = None) -> None:
    logger.info(
        event,
        run_id=str(read.run.run_id),
        project_id=read.run.carousel_project_id or "",
        phase=read.snapshot.phase,
        **(extra or {}),
    )


__all__ = ["GateRead", "GateRepairDependencies", "GateRepairStep"]
