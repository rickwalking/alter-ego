"""One run's gate as the tick read it, and what the runner sends from it.

Split out of ``gate_repair`` / ``runner`` because the model-fix step reads it
too.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.domain.gate import (
    GateSnapshot,
    OwnerReadyNotice,
    PolicyDecision,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)


@dataclass(frozen=True, kw_only=True)
class GateRead:
    """One run's gate as read this tick, and the policy's decision on it."""

    run: AutopilotRun
    snapshot: GateSnapshot
    decision: PolicyDecision


def escalation_command(read: GateRead, reason: str) -> TransitionCommand:
    """Escalate the run; ``detail`` lists the slides the model fix gave up on."""
    return TransitionCommand(
        run_id=read.run.run_id,
        expected=read.run.state,
        new=AutopilotRunState.ESCALATED,
        reason=reason,
        detail=read.decision.detail,
    )


def ready_notice(read: GateRead, project_id: str) -> OwnerReadyNotice:
    """The owner's ready notice for the final review."""
    return OwnerReadyNotice(
        run_id=read.run.run_id,
        project_id=project_id,
        revision=read.snapshot.lock_version,
        persona_score=read.snapshot.persona_score,
        sources_count=len(read.snapshot.sources),
    )


__all__ = ["GateRead", "escalation_command", "ready_notice"]
