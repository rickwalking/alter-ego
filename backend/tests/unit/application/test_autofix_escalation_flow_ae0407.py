"""AE-0407: the escalation to the reasoning model, on the real engine and runner.

Real: the SQLite rows and lock version, the LangGraph checkpoint, the
editorial facade, the autopilot snapshot, policy and runner. Fake: both
slide-fix chat models (``FakeChat``), the resume (recorded, not run).

Gherkin: tests/features/autofix_escalation_ae0407.feature
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.content_autofixer import (
    AutofixerConfig,
    InProcessContentAutofixer,
)
from rag_backend.modules.autopilot.quality_constants import REASON_CONTENT_QUALITY
from rag_backend.modules.editorial.public import REVIEW_ACTION_APPROVE
from tests.unit.application.content_gate_fixtures_ae0392 import (
    EMOJI_BODY_3,
    GateSeed,
    emoji_body_3,
)
from tests.unit.application.test_autopilot_slide_autofix_ae0401 import (
    CLEAN,
    CLEAN_BODY_3,
    STILL_EMOJI,
    _actions,
    _attempt_logs,
    _Flow,
    _flow,
    _pt,
    _Script,
)
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import _Notices, _Topics


def _factory(script: _Script, built: list[str]) -> Callable[[], BaseChatModel]:
    def build() -> BaseChatModel:
        built.append("built")
        return FakeChat(reply=script, log=CallLog())

    return build


async def _tick(
    flow: _Flow, reasoning: _Script, escalation_attempts: int = 2
) -> list[str]:
    built: list[str] = []
    autofixer = InProcessContentAutofixer(
        AutofixerConfig(
            session=flow.db,
            engine_factory=lambda: flow.engine,
            slide_fix_model=lambda: FakeChat(reply=flow.script, log=flow.log),
            autofix_escalation_attempts=escalation_attempts,
            slide_fix_escalation_model=_factory(reasoning, built),
        )
    )
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=flow.runs,
            topics=_Topics(),
            editorial=flow.gate,
            notices=_Notices(),
            recovery=_Recovery(runs=flow.runs),
            owner_user_id="owner",
            inputs=FakeProjectInputs(),
            autofix=autofixer,
            gate_repair=autofixer,
            slide_fix=autofixer,
        )
    )
    await runner.tick()
    return built


def _roles(logs: list[dict[str, object]]) -> list[tuple[object, object, object]]:
    return [(a["attempt"], a["model_role"], a["outcome"]) for a in _attempt_logs(logs)]


@pytest.mark.unit
@pytest.mark.asyncio
class TestEscalationFlow:
    async def test_fixed_on_attempt_4_approves(self, db_session: AsyncSession) -> None:
        """Scenario: Fixed on attempt 4 by the reasoning model, and the gate approves."""
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), [STILL_EMOJI])
        reasoning = _Script(answers=[CLEAN])
        with capture_logs() as logs:
            await _tick(flow, reasoning)
        assert _roles(logs) == [
            (1, "fast", "still_failing"),
            (2, "fast", "still_failing"),
            (3, "fast", "still_failing"),
            (4, "reasoning", "fixed"),
        ]
        assert len(flow.script.prompts) == 3
        assert len(reasoning.prompts) == 1
        assert (await _pt(flow, 3))["body"] == CLEAN_BODY_3
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]

    async def test_still_failing_after_5_escalates(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Still failing after 5 attempts escalates with every attempt counted."""
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), [STILL_EMOJI])
        reasoning = _Script(answers=[STILL_EMOJI])
        with capture_logs() as logs:
            await _tick(flow, reasoning)
        assert flow.runs.run.state is AutopilotRunState.ESCALATED
        assert flow.runs.run.state_reason == REASON_CONTENT_QUALITY
        detail = flow.runs.transitions[-1].detail
        assert "slide 3: visible_emoji_forbidden" in detail
        assert "(5 fix attempts)" in detail
        assert [role for _, role, _ in _roles(logs)] == ["fast"] * 3 + ["reasoning"] * 2
        assert (await _pt(flow, 3))["body"] == EMOJI_BODY_3

    async def test_escalation_attempts_0_never_builds_the_reasoning_model(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Escalation attempts 0 escalates after 3 attempts."""
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), [STILL_EMOJI])
        reasoning = _Script(answers=[CLEAN])
        built = await _tick(flow, reasoning, escalation_attempts=0)
        assert built == []
        assert reasoning.prompts == []
        assert "(3 fix attempts)" in flow.runs.transitions[-1].detail
        assert flow.runs.run.state is AutopilotRunState.ESCALATED
