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

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel import phase_artifact_runner
from rag_backend.application.services.carousel.content_budget_step import (
    BudgetStepInput,
    llm_budget_fitter,
    run_budget_step,
)
from rag_backend.application.services.carousel.content_gate_repair_targets import (
    FieldRepairTarget,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    FitRequest,
    FitTarget,
    LlmCopyBudgetConfig,
    LlmCopyBudgetFitter,
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
from rag_backend.domain.models.persona import PersonaProfile
from tests.unit.agents.content_feedback_flow_ae0405 import (
    GENERATE_TARGET,
    drafts_for,
    park_at_content,
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


@pytest.mark.unit
@pytest.mark.asyncio
class TestPersonaRescore:
    async def test_changed_slides_are_scored_again(self) -> None:
        """Scenario: Persona voice scores are recomputed for the changed slides."""
        fitter = FakeFitter()
        runner = PhaseArtifactRunner(
            PhaseArtifactRunnerConfig(
                outline_agent=MagicMock(),
                content_agent=MagicMock(),
                llm=MagicMock(),
                budget_fitter=fitter,
            )
        )
        scores = {"persona_scores": {"3": {"overall": 80.0}}}
        score_spy = AsyncMock(return_value={"persona_scores": {"3": {"overall": 75.0}}})
        runner._score_content_drafts = score_spy  # type: ignore[method-assign]
        persona = PersonaProfile(forbidden_phrases=["game changer"])
        resolved = EditorialWorkflowStartInput(
            topic="t", audience="a", brief="b", sources=[], persona=persona
        )
        long_slide = content_slide(3, pt_body=prose(PT_SENTENCES, 230), en_body="x")
        drafts: list[object] = [
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
        updates: dict[str, object] = {"slide_drafts": drafts, **scores}

        fit = await runner._fit_copy_budgets(
            {"project_id": "p"},  # type: ignore[arg-type]
            resolved,
            (drafts, updates, None),
        )

        assert fit.changed_indices == frozenset({3})
        assert updates["persona_scores"] == {"3": {"overall": 75.0}}
        rescored_drafts = score_spy.await_args.args[1]
        assert rescored_drafts[0]["draft_text"] == PT_ANSWERS[0]
        assert score_spy.await_args.args[2] == scores["persona_scores"]
        assert "game changer" in fitter.requests[0].style_guide

    async def test_without_a_fitter_the_drafts_pass_through(self) -> None:
        """Scenario: The shorten step runs before the presentation validation (off)."""
        drafts: list[object] = [{"slide_index": 1}, "not a draft"]
        updates: dict[str, object] = {}

        fit = await run_budget_step(
            None, BudgetStepInput("p", drafts, {"1": {}}), updates
        )

        assert fit.slide_drafts == [{"slide_index": 1}] and updates == {}
        assert fit.translations_en == {"1": {}}
        assert (
            await run_budget_step(None, BudgetStepInput("p", None, None), {})
        ).slide_drafts == []


@pytest.mark.unit
class TestFitterWiring:
    def test_fast_model_fitter_only_with_tracing(self) -> None:
        """Scenario: The shorten step runs before the presentation validation (wiring)."""

        def tracing() -> RunnableConfig:
            return RunnableConfig()

        assert llm_budget_fitter(MagicMock(), None) is None
        assert isinstance(llm_budget_fitter(MagicMock(), tracing), LlmCopyBudgetFitter)


@pytest.mark.unit
@pytest.mark.asyncio
class TestLlmFitter:
    async def test_one_traced_call_with_limits_and_parsed_fixes(self) -> None:
        """Scenario: Over-budget fields are rewritten within budget and pass (model call)."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content='{"fixes": [{"id": "3:en:body", "text": " Short. "}]}'
            )
        )
        configs: list[int] = []

        def tracing() -> RunnableConfig:
            configs.append(1)
            return RunnableConfig(tags=["fit"])

        target = FieldRepairTarget(
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
        request = FitRequest(
            targets=(
                FitTarget(target, FieldLimit("body", 220, max_lines=6, min_words=8)),
            ),
            style_guide="Never say game changer.",
        )
        fitter = LlmCopyBudgetFitter(
            LlmCopyBudgetConfig(llm=llm, runnable_config=tracing)
        )

        texts = await fitter.fit(request)

        prompt = str(llm.ainvoke.await_args.args[0][0].content)
        assert texts == {"3:en:body": "Short."}
        assert configs == [1]
        assert llm.ainvoke.await_args.args[1] == RunnableConfig(tags=["fit"])
        assert '"max_characters": 220' in prompt and '"min_words": 8' in prompt
        assert '"portuguese_source": "Um body longo."' in prompt
        assert "Never say game changer." in prompt
        assert render_fit_prompt(request) == prompt
