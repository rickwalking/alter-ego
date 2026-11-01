"""The content ensure shortens over-budget copy before the review is built.

Gherkin: tests/features/copy_fits_slide_budgets_ae0588.feature (section C).
Real engine + real artifact runner (the content feedback harness); the drafting
model and the fit model are fakes. One draft carries an over-long feature body,
so without the shorten step the content gate would block.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from rag_backend.agents import carousel_editorial_orchestrator as orchestrator_module
from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel import phase_artifact_runner
from rag_backend.application.services.carousel.content_budget_step import (
    BudgetStepInput,
    ContentBudgetContext,
    llm_budget_fitter,
    review_translations,
    run_budget_step,
    run_content_budget_step,
)
from rag_backend.application.services.carousel.content_gate_repair_targets import (
    FieldRepairTarget,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    FitRequest,
    FitTarget,
    LlmCopyBudgetConfig,
    LlmCopyBudgetFitter,
    model_bind_kwargs,
    render_fit_prompt,
)
from rag_backend.application.services.carousel.copy_budget_limits import FieldLimit
from rag_backend.application.services.carousel.editorial_workflow_generators import (
    SlideDraftGenerationParams,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.domain.constants.carousel_workflow import REVIEW_ACTION_APPROVE
from rag_backend.domain.constants.copy_budget_fit import COPY_BUDGET_TRACE_DETAIL
from rag_backend.domain.models.persona import PersonaProfile
from tests.unit.agents.content_feedback_flow_ae0405 import (
    GENERATE_TARGET,
    Review,
    drafts_for,
    park_at_content,
    review,
    state_of,
)
from tests.unit.application.copy_budget_fit_fixtures_ae0588 import (
    EN_ANSWERS,
    PT_ANSWERS,
    PT_SENTENCES,
    FakeFitter,
    content_slide,
    prose,
)

_LONG_FEATURE = (
    "Aplique no próximo ciclo com calma, revise cada passo com o time, registre o "
    "que mudou e compare com o ciclo anterior antes de seguir em frente."
)
_SHORT_FEATURE = "Aplique no próximo ciclo e compare com o anterior."
_SHORT_FEATURE_EN = "Apply it in the next cycle and compare it with the last one."
_REVIEW_TARGET = "build_fail_closed_review_updates"


def _over_budget_drafts() -> list[dict[str, object]]:
    drafts = drafts_for(1)
    features = cast(list[dict[str, object]], drafts[1]["features"])
    features[0] = {**features[0], "body": _LONG_FEATURE}
    return drafts


class _Drafter:
    async def __call__(
        self, _agent: object, _params: SlideDraftGenerationParams
    ) -> list[dict[str, object]]:
        return _over_budget_drafts()

    async def retry(self, _slide_index: int) -> dict[str, object] | None:
        return None


class _OrderedFitter(FakeFitter):
    """Fit double that writes into a shared event log."""

    def __init__(self, events: list[str]) -> None:
        super().__init__(answers={})
        self.events = events

    async def fit(self, request: FitRequest) -> dict[str, str]:
        self.events.append("fit")
        await super().fit(request)
        return {
            item.target.target_id: (
                _SHORT_FEATURE_EN if item.target.locale == "en" else _SHORT_FEATURE
            )
            for item in request.targets
            if item.target.field == "features[0].body"
        }


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    log: list[str] = []
    monkeypatch.setattr(GENERATE_TARGET, _Drafter())
    real = getattr(phase_artifact_runner, _REVIEW_TARGET)

    def spy(
        command: object,
    ) -> Awaitable[dict[str, object]]:
        log.append("review")
        return cast(Callable[[object], Awaitable[dict[str, object]]], real)(command)

    monkeypatch.setattr(phase_artifact_runner, _REVIEW_TARGET, spy)
    yield log


def _engine(fitter: FakeFitter) -> CarouselWorkflowEngine:
    runner = PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=MagicMock(),
            workflow_input=EditorialWorkflowStartInput(
                topic="Agentes", audience="devs", brief="b", sources=[]
            ),
            slide_draft_retry=_Drafter().retry,
            budget_fitter=fitter,
        )
    )
    return CarouselWorkflowEngine(checkpointer=InMemorySaver(), artifact_runner=runner)


def _feature_body(slide: dict[str, object], locale: str) -> str:
    payload = cast(dict[str, object], slide[f"presentation_{locale}"])
    return str(cast(list[dict[str, object]], payload["features"])[0]["body"])


@pytest.mark.unit
@pytest.mark.asyncio
class TestContentPhaseOrder:
    async def test_fit_runs_before_the_review_and_review_sees_short_copy(
        self, events: list[str]
    ) -> None:
        """Scenario: The shorten step runs before the presentation validation."""
        fitter = _OrderedFitter(events)
        engine = _engine(fitter)

        await park_at_content(engine)
        state = await state_of(engine)

        assert events[:2] == ["fit", "review"]
        assert fitter.calls == [["2:en:features[0].body", "2:pt:features[0].body"]]
        slides = cast(list[dict[str, object]], state["localized_slides"])
        second = next(slide for slide in slides if slide["slide_index"] == 2)
        assert _feature_body(second, "pt") == _SHORT_FEATURE
        assert _feature_body(second, "en") == _SHORT_FEATURE_EN
        report = cast(dict[str, object], state["presentation_validation"])
        codes = [
            cast(dict[str, object], v)["code"]
            for v in cast(list[object], report["violations"])
        ]
        assert "body_too_long" not in codes
        drafts = cast(list[dict[str, object]], state["slide_drafts"])
        assert _feature_body(drafts[1], "pt") == _SHORT_FEATURE

    async def test_parked_replay_never_calls_the_fitter(
        self, events: list[str]
    ) -> None:
        """Scenario: A parked content review replay never calls the fit model."""
        fitter = _OrderedFitter(events)
        engine = _engine(fitter)
        await park_at_content(engine)
        calls = len(fitter.calls)

        await review(engine, Review(REVIEW_ACTION_APPROVE))

        assert calls == 1
        assert len(fitter.calls) == calls
        assert events.count("fit") == 1


_SCORE_KEY = "slide_1"


def _over_budget_draft() -> list[object]:
    long_slide = content_slide(3, pt_body=prose(PT_SENTENCES, 230), en_body="x")
    return [
        {
            "slide_index": 3,
            "slide_type": "content",
            "policy_version": "hero_lower_third_v4",
            "title": "Revisões precisam de um dono",
            "draft_text": "x",
            "presentation_pt": long_slide["presentation_pt"],
            "presentation_en": {
                **cast(dict[str, object], long_slide["presentation_en"]),
                "body": EN_ANSWERS[3],
            },
        }
    ]


def _scorer(overall: float) -> AsyncMock:
    return AsyncMock(
        return_value={"persona_scores": {_SCORE_KEY: {"overall": overall}}}
    )


def _step(drafts: list[object], scorer: AsyncMock, old: float) -> BudgetStepInput:
    return BudgetStepInput(
        project_id="p",
        slide_drafts=drafts,
        translations_en={"3": {"heading": "Reviews need an owner", "body": "Old."}},
        scorer=scorer,
        previous_scores={_SCORE_KEY: {"overall": old, "text_sha256": "old"}},
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestPersonaRescore:
    async def test_changed_slides_are_scored_again(self) -> None:
        """Scenario: Persona voice scores are recomputed for the changed slides."""
        fitter = FakeFitter()
        scorer = _scorer(75.0)
        drafts = _over_budget_draft()
        updates: dict[str, object] = {}

        fit = await run_budget_step(fitter, _step(drafts, scorer, 80.0), updates)

        assert fit.changed_indices == frozenset({3})
        assert updates["persona_scores"] == {_SCORE_KEY: {"overall": 75.0}}
        rescored = scorer.await_args.args[0]
        assert rescored[0]["draft_text"] == PT_ANSWERS[0]
        assert scorer.await_args.args[1] == {
            _SCORE_KEY: {"overall": 80.0, "text_sha256": "old"}
        }
        assert updates["slide_drafts"] == fit.slide_drafts

    async def test_voice_drop_below_the_floor_reverts_the_slide(self) -> None:
        """Scenario: A shortening that drops the voice under the floor is undone."""
        fitter = FakeFitter()
        scorer = _scorer(60.0)
        drafts = _over_budget_draft()
        updates: dict[str, object] = {}

        fit = await run_budget_step(fitter, _step(drafts, scorer, 80.0), updates)

        assert len(fitter.calls) == 1 and scorer.await_count == 1
        assert fit.changed_indices == frozenset()
        assert fit.slide_drafts[0] == drafts[0]
        assert updates["slide_drafts"] == [drafts[0]]
        assert updates["persona_scores"] == {
            _SCORE_KEY: {"overall": 80.0, "text_sha256": "old"}
        }
        translations = cast(dict[str, dict[str, object]], fit.translations_en)
        assert translations["3"]["body"] == "Old."

    async def test_slide_already_under_the_floor_keeps_its_shortening(self) -> None:
        """Scenario: A shortening that drops the voice under the floor is undone (not when it was already under)."""
        scorer = _scorer(60.0)
        updates: dict[str, object] = {}

        fit = await run_budget_step(
            FakeFitter(), _step(_over_budget_draft(), scorer, 65.0), updates
        )

        assert fit.changed_indices == frozenset({3})
        assert updates["persona_scores"] == {_SCORE_KEY: {"overall": 60.0}}

    async def test_no_persona_scores_keep_the_fit(self) -> None:
        """Scenario: Persona voice scores are recomputed for the changed slides (no persona)."""
        updates: dict[str, object] = {}
        scorer = AsyncMock(return_value={})

        fit = await run_budget_step(
            FakeFitter(), _step(_over_budget_draft(), scorer, 80.0), updates
        )
        unscored = await run_budget_step(
            FakeFitter(),
            BudgetStepInput("p", _over_budget_draft(), None),
            {},
        )

        assert fit.changed_indices == frozenset({3}) == unscored.changed_indices
        assert "persona_scores" not in updates

    async def test_content_context_passes_persona_and_hook(self) -> None:
        """Scenario: Persona voice scores are recomputed for the changed slides (wiring)."""
        fitter = FakeFitter()
        scorer = _scorer(75.0)
        persona = PersonaProfile(forbidden_phrases=["game changer"])
        drafts = _over_budget_draft()
        updates: dict[str, object] = {"slide_drafts": drafts}

        fit = await run_content_budget_step(
            fitter,
            ContentBudgetContext(
                state={
                    "project_id": "p",
                    "presentation_policy_version": "hero_lower_third_v4",
                },
                updates=updates,
                slide_drafts=drafts,
                style_guide="Never say game changer.",
                persona=persona,
                outline=[{"slide_index": 1, "title": "Gancho"}, "bad"],
                scorer=scorer,
            ),
        )

        assert fit.changed_indices == frozenset({3})
        assert fitter.requests[0].style_guide == "Never say game changer."
        assert updates["persona_scores"] == {_SCORE_KEY: {"overall": 75.0}}

    async def test_without_a_fitter_the_drafts_pass_through(self) -> None:
        """Scenario: The shorten step runs before the presentation validation (off)."""
        drafts: list[object] = [{"slide_index": 1}, "not a draft"]
        updates: dict[str, object] = {}

        fit = await run_budget_step(
            None, BudgetStepInput("p", drafts, {"1": {}}), updates
        )

        assert fit.slide_drafts == [{"slide_index": 1}] and updates == {}
        assert fit.translations_en == {"1": {}}
        empty = await run_budget_step(None, BudgetStepInput("p", None, None), {})
        assert empty.slide_drafts == []


@pytest.mark.unit
class TestFitterWiring:
    def test_fast_model_fitter_only_with_tracing(self) -> None:
        """Scenario: The shorten step runs before the presentation validation (wiring)."""

        def tracing() -> RunnableConfig:
            return RunnableConfig()

        assert llm_budget_fitter(MagicMock(), None) is None
        assert isinstance(llm_budget_fitter(MagicMock(), tracing), LlmCopyBudgetFitter)

    def test_orchestrator_names_the_fit_trace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: The shorten step runs before the presentation validation (trace name)."""
        details: list[object] = []

        def fake_config(detail: str | None = None) -> RunnableConfig:
            details.append(detail)
            return RunnableConfig()

        monkeypatch.setattr(
            orchestrator_module, "get_langfuse_runnable_config", fake_config
        )
        orchestrator = orchestrator_module.CarouselEditorialOrchestrator(MagicMock())
        fitter = orchestrator._artifact_runner._budget_fitter
        assert isinstance(fitter, LlmCopyBudgetFitter)

        fitter._config.runnable_config()

        assert details == [COPY_BUDGET_TRACE_DETAIL] == ["copy budget fit"]

    def test_review_translations_prefer_fresh_ones(self) -> None:
        """Scenario: The shorten step runs before the presentation validation (translations)."""
        assert review_translations({"translations_en": {"1": {}}}, {}) == {"1": {}}
        assert review_translations({}, {"slide_drafts": []}) is None


def _target() -> FieldRepairTarget:
    return FieldRepairTarget(
        target_id="3:en:body",
        slide_index=3,
        locale="en",
        field="body",
        text="A long English body.",
        problems=("body_too_long: body exceeds max 220 characters (got 260)",),
        slide_heading="Revisões precisam de um dono",
        source_text="Um body longo.",
        max_characters=220,
        max_lines=6,
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestLlmFitter:
    async def test_one_traced_call_with_limits_and_parsed_fixes(self) -> None:
        """Scenario: Over-budget fields are rewritten within budget and pass (model call)."""
        bound = MagicMock()
        bound.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"fixes": [{"id": "3:en:body", "text": " Short. "}]}'
            )
        )
        llm = MagicMock()
        llm.bind = MagicMock(return_value=bound)
        configs: list[int] = []

        def tracing() -> RunnableConfig:
            configs.append(1)
            return RunnableConfig(tags=["fit"])

        request = FitRequest(
            targets=(
                FitTarget(_target(), FieldLimit("body", 220, max_lines=6, min_words=8)),
            ),
            style_guide="Never say game changer.",
        )
        fitter = LlmCopyBudgetFitter(
            LlmCopyBudgetConfig(llm=llm, runnable_config=tracing)
        )

        texts = await fitter.fit(request)

        prompt = str(bound.ainvoke.await_args.args[0][0].content)
        rendered, model_cfg = render_fit_prompt(request)
        assert texts == {"3:en:body": "Short."}
        assert configs == [1]
        assert bound.ainvoke.await_args.args[1] == RunnableConfig(tags=["fit"])
        llm.bind.assert_called_once_with(
            temperature=model_cfg["temperature"], max_tokens=model_cfg["max_tokens"]
        )
        assert model_cfg == {"temperature": 0.3, "max_tokens": 4096}
        assert '"max_characters": 220' in prompt and '"min_words": 8' in prompt
        assert '"portuguese_source": "Um body longo."' in prompt
        assert "Never say game changer." in prompt
        assert rendered == prompt

    async def test_no_model_block_calls_the_model_unbound(self) -> None:
        """Scenario: Over-budget fields are rewritten within budget and pass (no model block)."""
        assert model_bind_kwargs({}) == {}
        assert model_bind_kwargs({"temperature": True, "max_tokens": "x"}) == {}
        assert model_bind_kwargs({"temperature": 0.2, "top_p": 1}) == {
            "temperature": 0.2
        }
