"""Persona, voice gate, slide-1 photo and the scout's POV choice (PR #106 review).

Gherkin: tests/features/autopilot_pov_thesis.feature
("Persona and voice gate", "Slide-1 photo", "Scout POV format" sections)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.application.run_spec import (
    project_spec,
    spec_refusal,
    with_inputs,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    REASON_PASSED,
    REASON_PERSONA_SCORE,
    REASON_TOPIC_MISSING,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    ProjectSpec,
    StartCommand,
    StartStatus,
)
from rag_backend.modules.autopilot.domain.messages import StatusCopy, status_text
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.notify_constants import KIND_ESCALATED, KIND_FAILED
from rag_backend.modules.autopilot.pov_constants import (
    REASON_HOOK_PHOTO_MISSING,
    REASON_PERSONA_NOT_SCORED,
    TEXT_HOOK_PHOTO_MISSING,
    TEXT_PERSONA_NOT_SCORED,
)
from tests.unit.modules.autopilot.project_inputs_fake import (
    FAKE_HOOK_ASSET_ID,
    FAKE_PERSONA_ID,
    FakeProjectInputs,
)
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _OWNER,
    _Editorial,
    _Notices,
    _Recovery,
    _run,
    _Runs,
    _snapshot,
)
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _topic as _news_topic,
)

_S = AutopilotRunState
_THESIS = "Quem decide o que construir ainda é o dev."


def _content(score: float | None, *, pov: bool, revisions: int = 0) -> GateSnapshot:
    return replace(_snapshot(GATE_CONTENT, score, revisions), pov=pov)


def _pov_topic(**changes: object) -> TopicCandidate:
    topic = replace(
        _news_topic(uuid4()), content_mode="pov", thesis_draft="rascunho do scout"
    )
    return replace(topic, **changes)


def _pov_run() -> AutopilotRun:
    return replace(_run(_S.QUEUED), pov_thesis=_THESIS)


@dataclass
class _SpecEditorial(_Editorial):
    specs: list[ProjectSpec] = field(default_factory=list)
    started: list[StartCommand] = field(default_factory=list)

    async def create_project(self, spec: ProjectSpec) -> str:
        self.specs.append(spec)
        return await super().create_project(spec)

    async def start(self, command: StartCommand) -> StartStatus:
        self.started.append(command)
        return await super().start(command)


def _runner(
    runs: _Runs, editorial: _Editorial, inputs: FakeProjectInputs
) -> AutopilotRunner:
    return AutopilotRunner(
        RunnerDependencies(
            runs=runs,
            topics=runs,
            editorial=editorial,
            notices=_Notices(),
            recovery=_Recovery(runs=runs),
            owner_user_id=_OWNER,
            inputs=inputs,
        )
    )


@pytest.mark.unit
class TestVoiceGate:
    # Scenario: A POV carousel with no voice score escalates
    def test_unscored_pov_escalates_at_once(self) -> None:
        decision = decide(_content(None, pov=True))
        assert decision.action is GateAction.ESCALATE
        assert decision.reason == REASON_PERSONA_NOT_SCORED

    # Scenario: An unscored Radar IA carousel keeps AE-0364 (approved)
    def test_unscored_radar_ia_is_approved(self) -> None:
        decision = decide(_content(None, pov=False))
        assert decision.action is GateAction.APPROVE
        assert decision.reason == REASON_PASSED

    # Scenario: A scored POV carousel follows the voice floor
    def test_scored_pov_follows_the_floor(self) -> None:
        assert decide(_content(90.0, pov=True)).action is GateAction.APPROVE
        low = decide(_content(10.0, pov=True))
        assert low.action is GateAction.REVISE
        assert low.reason == REASON_PERSONA_SCORE


@pytest.mark.unit
class TestNotices:
    # Scenario: Telegram explains the POV persona escalation
    def test_persona_not_scored_notice(self) -> None:
        copy = StatusCopy(
            reason=REASON_PERSONA_NOT_SCORED, link="", permalink="", days_remaining=None
        )
        text = status_text(KIND_ESCALATED, copy)
        assert TEXT_PERSONA_NOT_SCORED in text
        assert "POV precisa da persona Pedro configurada" in text

    # Scenario: Telegram asks for a hook photo
    def test_hook_photo_missing_notice(self) -> None:
        copy = StatusCopy(
            reason=REASON_HOOK_PHOTO_MISSING, link="", permalink="", days_remaining=None
        )
        text = status_text(KIND_FAILED, copy)
        assert TEXT_HOOK_PHOTO_MISSING in text
        assert "dashboard" in text

    def test_other_reasons_are_quoted_as_before(self) -> None:
        copy = StatusCopy(
            reason="phase_failed",
            link="https://x.test/p",
            permalink="",
            days_remaining=None,
        )
        assert "phase_failed" in status_text(KIND_ESCALATED, copy)
        assert "https://x.test/p" in status_text(KIND_ESCALATED, copy)


@pytest.mark.unit
class TestRunSpec:
    # Scenario: The scout's POV format and slide count reach the carousel
    def test_scout_choice_is_carried(self) -> None:
        topic = _pov_topic(pov_format="erros_e_mitos", slide_count=8)
        spec = project_spec(_pov_run(), topic, _OWNER)
        assert spec.pov_format == "erros_e_mitos"
        assert spec.slide_count == 8
        assert spec.pov_thesis == _THESIS

    # Scenario: Defaults only when the scout chose nothing
    def test_defaults_when_absent(self) -> None:
        spec = project_spec(_pov_run(), _pov_topic(), _OWNER)
        assert spec.pov_format == "opiniao"
        assert spec.slide_count == 9

    def test_radar_ia_has_no_pov_choice(self) -> None:
        topic = replace(_news_topic(uuid4()), pov_format="opiniao", slide_count=8)
        spec = project_spec(_run(_S.QUEUED), topic, _OWNER)
        assert spec.pov_format is None
        assert spec.slide_count is None

    @pytest.mark.asyncio
    async def test_inputs_add_persona_everywhere_and_photo_for_pov(self) -> None:
        inputs = FakeProjectInputs()
        news = await with_inputs(
            project_spec(_run(_S.QUEUED), _news_topic(uuid4()), _OWNER), inputs
        )
        assert news.persona_id == FAKE_PERSONA_ID
        assert news.hook_asset_id is None
        assert inputs.hook_owners == []
        pov = await with_inputs(
            project_spec(_pov_run(), _pov_topic(), _OWNER),
            inputs,
        )
        assert pov.persona_id == FAKE_PERSONA_ID
        assert pov.hook_asset_id == FAKE_HOOK_ASSET_ID
        assert inputs.hook_owners == [_OWNER]

    def test_refusals(self) -> None:
        assert spec_refusal(None) == REASON_TOPIC_MISSING
        news = project_spec(_run(_S.QUEUED), _news_topic(uuid4()), _OWNER)
        assert spec_refusal(news) is None
        pov = project_spec(_pov_run(), _pov_topic(), _OWNER)
        assert spec_refusal(pov) == REASON_HOOK_PHOTO_MISSING
        assert spec_refusal(replace(pov, hook_asset_id=FAKE_HOOK_ASSET_ID)) is None


@pytest.mark.unit
class TestRunnerInputs:
    # Scenario: No hook photo, no POV run
    @pytest.mark.asyncio
    async def test_pov_without_photo_fails_before_any_carousel(self) -> None:
        runs = _Runs(run=_pov_run(), topic=_pov_topic())
        editorial = _SpecEditorial()
        await _runner(runs, editorial, FakeProjectInputs(hook=None)).tick()
        assert runs.run.state is _S.FAILED
        assert runs.run.state_reason == REASON_HOOK_PHOTO_MISSING
        assert editorial.specs == []
        assert editorial.starts == 0

    # Scenario: The POV carousel gets the persona, the photo and the scout choice
    @pytest.mark.asyncio
    async def test_pov_run_creates_with_persona_photo_and_choice(self) -> None:
        topic = _pov_topic(pov_format="comparacao", slide_count=10)
        runs = _Runs(run=_pov_run(), topic=topic)
        editorial = _SpecEditorial()
        await _runner(runs, editorial, FakeProjectInputs()).tick()
        assert runs.run.state is _S.GENERATING
        (spec,) = editorial.specs
        assert spec.persona_id == FAKE_PERSONA_ID
        assert spec.hook_asset_id == FAKE_HOOK_ASSET_ID
        assert (spec.pov_format, spec.slide_count) == ("comparacao", 10)
        assert editorial.started[0].spec.persona_id == FAKE_PERSONA_ID

    # Scenario: No persona configured: a Radar IA run still starts (unscored)
    @pytest.mark.asyncio
    async def test_radar_ia_without_persona_still_starts(self) -> None:
        runs = _Runs(run=_run(_S.QUEUED), topic=_news_topic(uuid4()))
        editorial = _SpecEditorial()
        await _runner(
            runs, editorial, FakeProjectInputs(persona=None, hook=None)
        ).tick()
        assert runs.run.state is _S.GENERATING
        assert editorial.specs[0].persona_id is None
