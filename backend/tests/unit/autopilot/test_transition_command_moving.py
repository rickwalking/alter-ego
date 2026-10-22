"""TransitionCommand.moving builds the compare-and-set for a run's current state.

Scenario: moving a run expects its current state and carries the reason.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)


# Scenario: moving a run expects its current state and carries the reason.
def test_moving_expects_current_state_and_carries_reason() -> None:
    run = SimpleNamespace(run_id=uuid4(), state=AutopilotRunState.AWAITING_OWNER)

    command = TransitionCommand.moving(run, AutopilotRunState.EXPIRED, "owner_expired")

    assert command == TransitionCommand(
        run_id=run.run_id,
        expected=AutopilotRunState.AWAITING_OWNER,
        new=AutopilotRunState.EXPIRED,
        reason="owner_expired",
    )
