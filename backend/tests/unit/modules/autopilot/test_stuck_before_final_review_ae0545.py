"""A run that died before the final review opened is re-driven, not waited on.

Feature: backend/tests/features/approve_keeps_caption_ae0545.feature
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.agents.carousel_workflow_engine import is_parked_before_node
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_STATUS_APPROVED,
)
from rag_backend.modules.autopilot.constants import (
    FIELD_CURRENT_PHASE,
    FIELD_PHASE_STATUS,
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
from rag_backend.modules.autopilot.infrastructure import editorial_driver
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
)
from rag_backend.modules.autopilot.parked_constants import (
    PARKED_GRACE_SECONDS,
    REASON_ENGINE_PARKED,
)
from rag_backend.modules.editorial.public import RunHeartbeat
from tests.unit.modules.autopilot.test_autopilot_runner import _snapshot

_PROJECT = "5350e0ca-ad31-40a1-9e50-70852f1ee484"
_NOW = datetime(2026, 10, 24, 3, 30, tzinfo=UTC)
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


class _Clock:
    def now(self) -> datetime:
        return _NOW


class _Handlers:
    async def get_state(self, _engine: object, _project_id: str) -> SimpleNamespace:
        state = {
            FIELD_CURRENT_PHASE: GATE_FINAL_REVIEW,
            FIELD_PHASE_STATUS: PHASE_STATUS_APPROVED,
        }
        return SimpleNamespace(state=state, lock_version=3)


def _acl() -> MagicMock:
    idle_since = _NOW - timedelta(seconds=PARKED_GRACE_SECONDS + 1)
    acl = MagicMock()
    acl.heartbeat = AsyncMock(
        return_value=RunHeartbeat(
            phase_status=PHASE_STATUS_APPROVED,
            heartbeat_at=None,
            updated_at=idle_since,
        )
    )
    acl.slide_total = AsyncMock(return_value=7)
    acl.hero_image_total = AsyncMock(return_value=0)
    acl.is_pov = AsyncMock(return_value=False)
    acl.load_project = AsyncMock(return_value=None)
    return acl


@pytest.mark.parametrize("pending", [True, False])
async def test_the_runner_asks_the_engine_whether_a_node_is_pending(
    monkeypatch: pytest.MonkeyPatch, pending: bool
) -> None:
    """Scenario: A workflow stuck before the final review interrupt is re-driven"""
    engine = MagicMock()
    engine.is_parked_before_node = AsyncMock(return_value=pending)
    monkeypatch.setattr(editorial_driver, "_handlers", lambda _session: _Handlers())
    driver = InProcessEditorialDriver(
        EditorialDriverConfig(
            session=AsyncMock(),
            engine_factory=lambda: engine,
            clock=_Clock(),
            stale_after_seconds=180,
        )
    )
    monkeypatch.setattr(driver, "_acl", _acl())

    gate = await driver.read_gate(_PROJECT)

    engine.is_parked_before_node.assert_awaited_once_with(_PROJECT)
    assert (gate.parked, gate.parked_overdue) == (pending, pending)
