"""The autopilot model fix of failing slides, on the real engine.

Real: the SQLite rows and lock version, ``EditorialWorkflowService`` with a
LangGraph checkpoint, the editorial facade (gate repair + slide fix), the
autopilot snapshot, policy and runner. Fake: the slide-fix chat model
(``tests/unit/llm_fakes_ae0391.FakeChat``), the resume (recorded, not run).

Gherkin: tests/features/autopilot_slide_autofix_ae0401.feature
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import cast

import pytest
from langchain_core.language_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.application.services.carousel import owner_autofix_lock
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_DESIGN
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.autofix_constants import LOG_SLIDE_AUTOFIX
from rag_backend.modules.autopilot.constants import REASON_FORBIDDEN
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.infrastructure.content_autofixer import (
    AutofixerConfig,
    InProcessContentAutofixer,
)
from rag_backend.modules.autopilot.quality_constants import REASON_CONTENT_QUALITY
from rag_backend.modules.editorial.public import (
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)
from tests.unit.application.content_gate_fixtures_ae0392 import (
    EMOJI_BODY_3,
    FIXED_HEADING_5,
    FORBIDDEN_PHRASE,
    GateSeed,
    RealGate,
    emoji_body_3,
    lowercase_heading_5,
    seed_gate,
)
from tests.unit.application.owner_autofix_fixtures_ae0367 import (
    LOCK_VERSION,
    FakeChatModel,
    build_engine,
    row,
)
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _Notices,
    _Runs,
    _Topics,
    _world,
)

CLEAN_BODY_3 = "O Argon resiste a ataques indiretos hoje."
EMOJI_HEADING_3 = "Ponto de conteúdo 🚀 número 3"


def _answer(body: str, heading: str | None = None) -> str:
    copy: dict[str, str] = {"body": body}
    if heading is not None:
        copy["heading"] = heading
    return "```json\n" + json.dumps({"pt": copy}, ensure_ascii=False) + "\n```"


CLEAN = _answer(CLEAN_BODY_3)
STILL_EMOJI = _answer(EMOJI_BODY_3)


@dataclass
class _Script:
    """Answers in order (the last repeats); an Exception entry is raised."""

    answers: list[str | Exception]
    prompts: list[str] = field(default_factory=list)

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        index = min(len(self.prompts), len(self.answers)) - 1
        answer = self.answers[index]
        if isinstance(answer, Exception):
            raise answer
        return answer


@dataclass
class _RecordingRuns(_Runs):
    transitions: list[TransitionCommand] = field(default_factory=list)

    async def transition(self, command: TransitionCommand) -> bool:
        self.transitions.append(command)
        return await super().transition(command)


@dataclass
class _Flow:
    db: AsyncSession
    project_id: str
    engine: EditorialWorkflowService
    gate: RealGate
    runs: _RecordingRuns
    script: _Script
    log: CallLog


async def _flow(
    db: AsyncSession, seed: GateSeed, answers: list[str | Exception]
) -> _Flow:
    engine = build_engine(FakeChatModel())
    project_id = await seed_gate(engine, db, seed)
    base = _world()
    run = replace(
        base.runs.run,
        carousel_project_id=project_id,
        state=AutopilotRunState.GENERATING,
    )
    return _Flow(
        db=db,
        project_id=project_id,
        engine=engine,
        gate=RealGate(db=db, engine=engine),
        runs=_RecordingRuns(run=run),
        script=_Script(answers=answers),
        log=CallLog(),
    )


def _model(flow: _Flow) -> Callable[[], BaseChatModel]:
    return lambda: FakeChat(reply=flow.script, log=flow.log)


async def _tick(flow: _Flow) -> None:
    autofixer = InProcessContentAutofixer(
        AutofixerConfig(
            session=flow.db,
            engine_factory=lambda: flow.engine,
            slide_fix_model=_model(flow),
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


async def _lock_version(flow: _Flow) -> int:
    version = await flow.db.scalar(
        select(CarouselProjectModel.lock_version).where(
            CarouselProjectModel.id == flow.project_id
        )
    )
    return int(version or 0)


async def _state(flow: _Flow) -> dict[str, object]:
    state = await flow.engine.get_workflow_state(flow.project_id)
    assert state is not None
    return dict(state)


async def _pt(flow: _Flow, index: int) -> dict[str, object]:
    slides = cast(list[dict[str, object]], (await _state(flow))["localized_slides"])
    return cast(dict[str, object], slides[index - 1]["presentation_pt"])


def _actions(flow: _Flow) -> list[str]:
    return [command.action for command in flow.gate.resumes]


def _attempt_logs(logs: list[dict[str, object]]) -> list[dict[str, object]]:
    return [log for log in logs if log["event"] == LOG_SLIDE_AUTOFIX]


@pytest.mark.unit
@pytest.mark.asyncio
class TestSlideAutofixFlow:
    """Scenarios of autopilot_slide_autofix_ae0401.feature, real engine."""

    async def test_deterministic_fix_needs_no_model(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Fixed deterministically, approved without a model call.

        The rows render the repaired copy.
        """
        flow = await _flow(db_session, GateSeed(breaks=(lowercase_heading_5,)), [CLEAN])
        await _tick(flow)
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]
        assert flow.log.models == []
        assert (await row(flow.db, flow.project_id, 5)).heading == FIXED_HEADING_5

    async def test_fixed_on_attempt_1(self, db_session: AsyncSession) -> None:
        """Scenario: Fixed on attempt 1."""
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), [CLEAN])
        with capture_logs() as logs:
            await _tick(flow)
        assert (await _pt(flow, 3))["body"] == CLEAN_BODY_3
        assert (await row(flow.db, flow.project_id, 3)).body == CLEAN_BODY_3
        state = await _state(flow)
        assert state["content_gate_validation"] == {}
        drafts = cast(list[dict[str, object]], state["slide_drafts"])
        assert drafts[2]["draft_text"] == CLEAN_BODY_3
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]
        assert flow.gate.resumes[0].expected_version == LOCK_VERSION + 1
        attempts = _attempt_logs(logs)
        assert [(a["slide"], a["attempt"], a["outcome"]) for a in attempts] == [
            (3, 1, "fixed")
        ]
        assert attempts[0]["rules_before"] == ["visible_emoji_forbidden"]
        assert attempts[0]["rules_after"] == []
        assert attempts[0]["run_id"] == str(flow.runs.run.run_id)
        assert "visible_emoji_forbidden" in flow.script.prompts[0]

    async def test_fixed_on_attempt_3(self, db_session: AsyncSession) -> None:
        """Scenario: Fixed on attempt 3."""
        answers: list[str | Exception] = [STILL_EMOJI, STILL_EMOJI, CLEAN]
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), answers)
        with capture_logs() as logs:
            await _tick(flow)
        outcomes = [a["outcome"] for a in _attempt_logs(logs)]
        assert outcomes == ["still_failing", "still_failing", "fixed"]
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]

    async def test_still_failing_escalates_with_the_slides(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Still failing after 3 attempts escalates with the slides listed.

        3 fast attempts then 2 on the reasoning model (here the same
        fake), so 5 attempts are counted.
        """
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), [STILL_EMOJI])
        await _tick(flow)
        assert flow.runs.run.state is AutopilotRunState.ESCALATED
        assert flow.runs.run.state_reason == REASON_CONTENT_QUALITY
        detail = flow.runs.transitions[-1].detail
        assert "slide 3: visible_emoji_forbidden" in detail
        assert EMOJI_BODY_3 in detail
        assert "(5 fix attempts)" in detail
        assert flow.gate.resumes == []
        assert len(flow.script.prompts) == 5
        assert (await _pt(flow, 3))["body"] == EMOJI_BODY_3
        assert await _lock_version(flow) == LOCK_VERSION

    async def test_model_error_counts_as_an_attempt(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A model error counts as an attempt."""
        answers: list[str | Exception] = [RuntimeError("provider down"), CLEAN]
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), answers)
        with capture_logs() as logs:
            await _tick(flow)
        outcomes = [a["outcome"] for a in _attempt_logs(logs)]
        assert outcomes == ["model_error", "fixed"]
        assert "The previous attempt failed" in flow.script.prompts[1]
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]

    async def test_unparseable_answer_counts_as_an_attempt(
        self, db_session: AsyncSession
    ) -> None:
        answers: list[str | Exception] = ["Sure, here it is", CLEAN]
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), answers)
        with capture_logs() as logs:
            await _tick(flow)
        assert [a["outcome"] for a in _attempt_logs(logs)] == ["unparseable", "fixed"]
        assert "model_output_unparseable" in flow.script.prompts[1]

    async def test_a_new_violation_is_fed_back(self, db_session: AsyncSession) -> None:
        """Scenario: A fix that breaks another rule is retried with the new violation."""
        answers: list[str | Exception] = [
            _answer(CLEAN_BODY_3, heading=EMOJI_HEADING_3),
            _answer(CLEAN_BODY_3, heading="Ponto de conteúdo número 3"),
        ]
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), answers)
        await _tick(flow)
        assert "visible_emoji_forbidden (pt heading)" in flow.script.prompts[1]
        assert EMOJI_HEADING_3 in flow.script.prompts[1]
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]

    async def test_no_progress_escalates_and_never_loops(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Repair makes no progress, the model fix runs, then escalates."""
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), [STILL_EMOJI])
        with capture_logs() as logs:
            await _tick(flow)
            await _tick(flow)
        events = [log["event"] for log in logs]
        assert events.count("autopilot_gate_repair_noop") == 1
        assert len(_attempt_logs(logs)) == 5
        assert flow.runs.run.state is AutopilotRunState.ESCALATED
        escalations = [
            t for t in flow.runs.transitions if t.new is AutopilotRunState.ESCALATED
        ]
        assert len(escalations) == 1

    @pytest.mark.parametrize("revisions", [0, 2])
    async def test_never_revises_content_quality(
        self, db_session: AsyncSession, revisions: int
    ) -> None:
        """Scenario: No revise is ever issued for content quality."""
        seed = GateSeed(breaks=(emoji_body_3,), revisions=revisions)
        flow = await _flow(db_session, seed, [STILL_EMOJI])
        await _tick(flow)
        assert REVIEW_ACTION_REVISE not in _actions(flow)
        assert flow.runs.run.state is AutopilotRunState.ESCALATED

    async def test_design_gate_gets_the_same_fix(
        self, db_session: AsyncSession
    ) -> None:
        seed = GateSeed(breaks=(emoji_body_3,), phase=PHASE_DESIGN)
        flow = await _flow(db_session, seed, [CLEAN])
        await _tick(flow)
        assert (await _pt(flow, 3))["body"] == CLEAN_BODY_3
        assert _actions(flow) == [REVIEW_ACTION_APPROVE]

    async def test_a_lost_lock_writes_nothing(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: A lost lock writes nothing and retries next tick."""
        flow = await _flow(db_session, GateSeed(breaks=(emoji_body_3,)), [CLEAN])

        async def _moved(*args: object, **kwargs: object) -> int:
            raise ValueError(ERR_VERSION_CONFLICT)

        monkeypatch.setattr(
            owner_autofix_lock.CarouselProjectWriteOwner,
            "bump_resume_lock_version",
            _moved,
        )
        with capture_logs() as logs:
            await _tick(flow)
        assert "autopilot_slide_autofix_conflict" in [log["event"] for log in logs]
        assert flow.gate.resumes == []
        assert flow.runs.run.state is AutopilotRunState.GENERATING
        assert (await _pt(flow, 3))["body"] == EMOJI_BODY_3

    async def test_other_reasons_keep_the_revise(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Other reasons keep the revise path."""
        flow = await _flow(db_session, GateSeed(), [CLEAN])
        flow.gate.forbidden_hits = (FORBIDDEN_PHRASE,)
        await _tick(flow)
        assert _actions(flow) == [REVIEW_ACTION_REVISE]
        assert f"Reason: {REASON_FORBIDDEN}." in flow.gate.resumes[0].feedback
        assert flow.log.models == []
