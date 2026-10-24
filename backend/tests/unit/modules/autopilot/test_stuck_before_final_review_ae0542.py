"""A run that died before the final review opened is re-driven, not waited on.

Feature: backend/tests/features/approve_keeps_caption_ae0542.feature
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from rag_backend.agents.carousel_workflow_engine import is_parked_before_node
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_STATUS_APPROVED,
)
from rag_backend.modules.autopilot.constants import (
    GATE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING,
)
from rag_backend.modules.autopilot.domain.gate import GateAction
from rag_backend.modules.autopilot.domain.parked import (
    GateStatus,
    GateStatusInput,
    RowRun,
    reconcile_gate_status,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.parked_constants import (
    PARKED_GRACE_SECONDS,
    REASON_ENGINE_PARKED,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _snapshot

_IDLE = RowRun(
    phase_status=PHASE_STATUS_APPROVED, idle_seconds=PARKED_GRACE_SECONDS + 1
)


def _final_review(node_pending: bool) -> GateStatus:
    return reconcile_gate_status(
        GateStatusInput(
            engine_phase=GATE_FINAL_REVIEW,
            engine_status=PHASE_STATUS_APPROVED,
            row=_IDLE,
            grace_seconds=PARKED_GRACE_SECONDS,
            node_pending=node_pending,
        )
    )


def test_a_final_review_that_never_opened_is_parked_and_redriven() -> None:
    """Scenario: A workflow stuck before the final review interrupt is re-driven"""
    status = _final_review(node_pending=True)
    assert status == GateStatus(
        phase_status=PHASE_STATUS_APPROVED, parked=True, parked_overdue=True
    )
    snapshot = replace(
        _snapshot(GATE_FINAL_REVIEW, 90.0, 0),
        phase_status=status.phase_status,
        parked=status.parked,
        parked_overdue=status.parked_overdue,
    )
    decision = decide(snapshot)
    assert (decision.action, decision.reason) == (
        GateAction.REDRIVE,
        REASON_ENGINE_PARKED,
    )


def test_a_held_approved_carousel_is_still_never_parked() -> None:
    """Scenario: A workflow stuck before the final review interrupt is re-driven"""
    assert _final_review(node_pending=False) == GateStatus(
        phase_status=PHASE_STATUS_APPROVED
    )


def test_the_engine_reports_a_pending_final_review_but_not_the_hold() -> None:
    """Scenario: A workflow stuck before the final review interrupt is re-driven"""
    stuck = SimpleNamespace(next=(GATE_FINAL_REVIEW,), interrupts=(), tasks=())
    held = SimpleNamespace(next=(PHASE_APPROVED_HOLD,), interrupts=(), tasks=())
    open_review = SimpleNamespace(
        next=(GATE_FINAL_REVIEW,),
        interrupts=(),
        tasks=(SimpleNamespace(interrupts=(PHASE_STATUS_AWAITING,)),),
    )
    assert is_parked_before_node(stuck) is True
    assert is_parked_before_node(held) is False
    assert is_parked_before_node(open_review) is False
