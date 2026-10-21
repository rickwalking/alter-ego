"""The autopilot approves an unscored content gate into design.

Feature: autopilot_runner.feature (unscored persona scenarios)

Prod 2026-10-14, carousel 8e350d6e: the autopilot attaches no persona, so the
content phase wrote 7 drafts and ``persona_scores = {}``. The engine allows
that approve; the policy revised it until the cap. This drives the real
``EditorialWorkflowService``, graph, checkpointer and run wrapper (the resume
world); only the LLM artifact generation is faked.

The drafts pass the presentation check, so only the persona rule is tested.
"""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_DESIGN,
    PHASE_STATUS_AWAITING,
    REASON_PASSED,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    ResumeCommand,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.policy import decide
from tests.integration import test_autopilot_resume_runs_phase as ae0363
from tests.integration.test_autopilot_resume_runs_phase import _approve, world

__all__ = ["world"]

_SLIDES = 7
_DRAFTS = [
    {
        "heading": f"Agents ship {i}",
        "body": "Short body text.",
        "draft_text": f"Agents ship {i}. Short body text.",
    }
    for i in range(_SLIDES)
]


@pytest.mark.asyncio
async def test_unscored_content_gate_is_approved_and_moves_to_design(
    world: ae0363._World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: The autopilot approves an unscored content gate and the workflow moves to design."""
    monkeypatch.setattr(ae0363, "_DRAFTS", _DRAFTS)
    assert await _approve(world) is ResumeStatus.APPLIED
    gate = await world.driver.read_gate(world.project_id)
    assert (gate.phase, gate.phase_status) == (GATE_CONTENT, PHASE_STATUS_AWAITING)
    state = await world.service.get_workflow_state(world.project_id)
    assert state is not None
    assert len(state.get("slide_drafts") or []) == _SLIDES
    assert not state.get("persona_scores")
    assert gate.persona_score is None
    assert gate.engine_blocker == ""

    decision = decide(gate)
    assert decision.action is GateAction.APPROVE
    assert decision.reason == REASON_PASSED
    result = await world.driver.resume(
        ResumeCommand(
            project_id=world.project_id,
            action="approve",
            expected_version=gate.lock_version,
            feedback="",
            phase=gate.phase,
        )
    )

    assert result.status is ResumeStatus.APPLIED
    after = await world.service.get_workflow_state(world.project_id)
    assert after is not None
    assert after.get("content_approved")
    assert (after.get("current_phase"), after.get("phase_status")) == (
        GATE_DESIGN,
        PHASE_STATUS_AWAITING,
    )
    design = await world.driver.read_gate(world.project_id)
    assert (design.phase, design.phase_status) == (GATE_DESIGN, PHASE_STATUS_AWAITING)
