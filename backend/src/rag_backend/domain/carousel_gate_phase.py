"""The review gate a carousel workflow checkpoint is parked at.

Pure over a LangGraph state snapshot (duck-typed: ``values`` and ``next``), so
both the engine (agents) and the structured-feedback guard (application) use
the same rule without a cross-layer import.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_WORKFLOW_PHASES,
    PHASE_APPROVED_HOLD,
)

_CURRENT_PHASE = "current_phase"


def _has_open_interrupt(snapshot: object) -> bool:
    if getattr(snapshot, "interrupts", ()) or ():
        return True
    tasks = getattr(snapshot, "tasks", ()) or ()
    return any(getattr(task, "interrupts", ()) for task in tasks)


def checkpoint_gate_phase(snapshot: object) -> str:
    """The phase of the review gate the checkpoint is parked at.

    An interrupted node's return value is never committed, so on the FIRST
    gate of a phase the stored ``current_phase`` still names the node before
    it (``outline`` at the first content gate). The pending node is the gate
    the reviewer sees, the same rule ``CarouselWorkflowEngine.get_state``
    applies. Only an OPEN review interrupt makes the pending node a gate: the
    approved-hold park, a finished graph and a run parked before a
    node with no interrupt yet keep the stored value.
    """
    values = getattr(snapshot, "values", None)
    if not isinstance(values, dict):
        return ""
    stored = str(values.get(_CURRENT_PHASE, ""))
    pending_next = getattr(snapshot, "next", ()) or ()
    if not pending_next or not _has_open_interrupt(snapshot):
        return stored
    node = str(pending_next[0])
    if node == PHASE_APPROVED_HOLD or node not in CAROUSEL_WORKFLOW_PHASES:
        return stored
    return node


__all__ = ["checkpoint_gate_phase"]
