"""An unscored persona judge never escalates a passing run (real engine).

Real: the SQLite rows and lock version, the LangGraph checkpoint, the
editorial facade (slide fix + persona scorer + persisted scores), the
autopilot snapshot, policy and runner. Fake: the chat models (``FakeChat``;
the persona judge and the rewriter share it, told apart by the prompt), the
project persona, the resume (recorded, not run).

Gherkin: tests/features/autopilot_unscored_judge_ae0433.feature
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

import pytest
from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.autofix_constants import (
    LOG_SLIDE_AUTOFIX_ESCALATED,
    LOG_SLIDE_AUTOFIX_UNSCORED,
    REASON_PERSONA_JUDGE_UNAVAILABLE,
)
from rag_backend.modules.autopilot.constants import REASON_PERSONA_SCORE
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.content_autofixer import (
    AutofixerConfig,
    InProcessContentAutofixer,
)
from rag_backend.modules.editorial.infrastructure.pov_inputs import PovInputsAcl
from rag_backend.modules.editorial.public import REVIEW_ACTION_APPROVE
from tests.unit.application.content_gate_fixtures_ae0392 import GateSeed
from tests.unit.application.test_autopilot_slide_autofix_ae0401 import (
    _actions,
    _Flow,
    _flow,
    _pt,
    _state,
)
from tests.unit.llm_fakes_ae0391 import FakeChat
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import _Notices, _Topics

SLIDE = 3
REWRITTEN_3 = "Eu testo o Argon contra ataques indiretos antes de confiar nele."
JUDGE_MARKER = "Score this content"
REWRITE = "```json\n" + json.dumps({"pt": {"body": REWRITTEN_3}}) + "\n```"


def _scored(overall: float) -> str:
    return json.dumps({"overall": overall, "tone_match": overall})


@dataclass
class _Judge:
    """The judge's answers in order (the last repeats); an Exception is raised."""

    answers: list[str | Exception]
    texts: list[str] = field(default_factory=list)

    def __call__(self, prompt: str) -> str:
        self.texts.append(prompt)
        answer = self.answers[min(len(self.texts), len(self.answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer


@dataclass
class _Models:
    """The fast model (rewrites + judge) and the next model of its queue."""

    judge: _Judge
    fallback_judge: _Judge | None = None
    rewrites: list[str] = field(default_factory=list)

    def reply(self, prompt: str) -> str:
        if JUDGE_MARKER in prompt:
            return self.judge(prompt)
        self.rewrites.append(prompt)
        return REWRITE

    def build(self) -> BaseChatModel:
        fallback = None
        if self.fallback_judge is not None:
            fallback = FakeChat(reply=self.fallback_judge)
        return _QueueChat(reply=self.reply, fallback=fallback)


class _QueueChat(FakeChat):
    """A ``FakeChat`` whose ``as_fallback`` is the next model of the queue."""

    fallback: FakeChat | None = None

    def as_fallback(self) -> BaseChatModel | None:
        return self.fallback


def _scores(slide_3: dict[str, object]) -> dict[str, object]:
    scores: dict[str, object] = {
        f"slide_{n}": {"overall": 80.0, "tone_match": 80.0} for n in range(1, 8)
    }
    scores[f"slide_{SLIDE}"] = slide_3
    return scores


@pytest.fixture(autouse=True)
def _persona(monkeypatch: pytest.MonkeyPatch) -> None:
    async def project_persona(
        self: PovInputsAcl, project_id: str
    ) -> PersonaProfile | None:
        del self, project_id
        return PersonaProfile(name="Pedro")

    monkeypatch.setattr(PovInputsAcl, "project_persona", project_persona)


async def _seeded(db: AsyncSession, slide_3: dict[str, object]) -> _Flow:
    flow = await _flow(db, GateSeed(), [REWRITE])
    await flow.engine.update_workflow_state(
        flow.project_id, {"persona_scores": _scores(slide_3)}
    )
    return flow


async def _tick(flow: _Flow, models: _Models, max_ticks: int = 3) -> None:
    model: Callable[[], BaseChatModel] = models.build
    autofixer = InProcessContentAutofixer(
        AutofixerConfig(
            session=flow.db,
            engine_factory=lambda: flow.engine,
            slide_fix_model=model,
            persona_unscored_max_ticks=max_ticks,
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


async def _entry(flow: _Flow) -> dict[str, object]:
    scores = cast(dict[str, dict[str, object]], (await _state(flow))["persona_scores"])
    return scores[f"slide_{SLIDE}"]


def _events(logs: list[dict[str, object]], event: str) -> list[dict[str, object]]:
    return [log for log in logs if log["event"] == event]


LOW = {"overall": 55.0, "tone_match": 55.0}
PENDING = {**LOW, "rescore_pending": True, "unscored_ticks": 1}


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnscoredJudgeFlow:
    async def test_timeout_then_fallback_score_approves(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Judge timeout then success on the fallback approves the gate."""
        flow = await _seeded(db_session, LOW)
        models = _Models(
            judge=_Judge([TimeoutError()]), fallback_judge=_Judge([_scored(82.0)])
        )
        await _tick(flow, models)
        entry = await _entry(flow)
        assert entry["overall"] == 82.0
        assert "rescore_pending" not in entry
        assert (await _pt(flow, SLIDE))["body"] == REWRITTEN_3
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]
        assert flow.runs.run.state is AutopilotRunState.GENERATING

    async def test_unscored_judge_stays_generating(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: An unscored judge leaves the run generating and marks the slide."""
        flow = await _seeded(db_session, LOW)
        models = _Models(
            judge=_Judge([TimeoutError()]), fallback_judge=_Judge([TimeoutError()])
        )
        with capture_logs() as logs:
            await _tick(flow, models)
        assert flow.runs.run.state is AutopilotRunState.GENERATING
        assert flow.runs.transitions == []
        assert _actions(flow) == []
        assert await _entry(flow) == {**PENDING}
        assert (await _pt(flow, SLIDE))["body"] == REWRITTEN_3
        assert _events(logs, LOG_SLIDE_AUTOFIX_ESCALATED) == []
        unscored = _events(logs, LOG_SLIDE_AUTOFIX_UNSCORED)
        assert [(u["unscored_slides"], u["judge_unavailable"]) for u in unscored] == [
            ([SLIDE], False)
        ]

    async def test_pending_slide_is_rescored_next_tick(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A pending slide is re-scored on the next tick without a rewrite."""
        flow = await _seeded(db_session, LOW)
        down = _Models(judge=_Judge([TimeoutError()]))
        await _tick(flow, down)
        assert (await _entry(flow))["rescore_pending"] is True
        back = _Models(judge=_Judge([_scored(80.0)]))
        await _tick(flow, back)
        assert back.rewrites == []
        assert back.judge.texts and REWRITTEN_3 in back.judge.texts[0]
        assert await _entry(flow) == {"overall": 80.0, "tone_match": 55.0}
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]

    async def test_judge_that_stays_down_escalates_its_own_reason(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A judge that stays unavailable escalates with its own reason."""
        flow = await _seeded(db_session, PENDING)
        models = _Models(judge=_Judge([TimeoutError()]))
        await _tick(flow, models, max_ticks=2)
        assert models.rewrites == []
        assert flow.runs.run.state is AutopilotRunState.ESCALATED
        assert flow.runs.run.state_reason == REASON_PERSONA_JUDGE_UNAVAILABLE
        assert "slides 3" in flow.runs.transitions[-1].detail
        assert (await _entry(flow))["unscored_ticks"] == 2

    async def test_real_low_score_still_escalates(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A real low score still escalates on the voice floor."""
        flow = await _seeded(db_session, LOW)
        models = _Models(judge=_Judge([_scored(50.0)]))
        await _tick(flow, models)
        assert flow.runs.run.state is AutopilotRunState.ESCALATED
        assert flow.runs.run.state_reason == REASON_PERSONA_SCORE
        assert "slide 3: voice_score_low" in flow.runs.transitions[-1].detail
        assert await _entry(flow) == LOW
