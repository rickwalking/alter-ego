"""The copy-budget fit reaches the fallback model inside its own deadline.

Gherkin: tests/features/copy_budget_fit_fallback_ae0607.feature.
The fit runs on the real fitter (prompt, bind, parse) and the real validator;
only the two chat models are doubles with a chosen delay and answer.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import cast
from unittest.mock import MagicMock

import pytest
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable, RunnableConfig
from structlog.testing import capture_logs

from rag_backend.agents import carousel_editorial_orchestrator as orchestrator_module
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel import copy_budget_fit
from rag_backend.application.services.carousel.copy_budget_fit import (
    BudgetFitCommand,
    fit_slides_to_budgets,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    FitRequest,
    LlmCopyBudgetConfig,
    LlmCopyBudgetFitter,
    render_fit_prompt,
)
from rag_backend.domain.constants.copy_budget_fit import (
    COPY_BUDGET_FIT_PRIMARY_SECONDS,
    COPY_BUDGET_FIT_TIMEOUT_SECONDS,
    COPY_BUDGET_PROMPT_DOMAIN,
    COPY_BUDGET_PROMPT_FIT,
    COPY_BUDGET_PROMPT_VERSION,
    LOG_COPY_BUDGET_FIT_FALLBACK_USED,
    LOG_COPY_BUDGET_FIT_MODEL_FAILED,
)
from tests.unit.application.copy_budget_fit_fixtures_ae0588 import (
    EN_SENTENCES,
    POLICY_V4,
    PT_ANSWERS,
    PT_SENTENCES,
    content_slide,
    prose,
)

_FIELD_ID = "3:pt:body"
_LONG_PT = prose(PT_SENTENCES, 300)
_STILL_LONG_PT = prose(PT_SENTENCES, 230)
_PRIMARY_TEXT = PT_ANSWERS[0]
_FALLBACK_TEXT = PT_ANSWERS[1]
_WINDOW = 0.05
_SLOW = 5.0


def _fixes(text: str) -> str:
    return json.dumps({"fixes": [{"id": _FIELD_ID, "text": text}]}, ensure_ascii=False)


@dataclass
class _Model:
    """A chat model double: waits ``delay`` seconds, then answers or raises."""

    answers: list[str] = field(default_factory=list)
    delay: float = 0.0
    error: Exception | None = None
    calls: int = 0
    bound: list[dict[str, object]] = field(default_factory=list)

    def bind(self, **kwargs: object) -> _Model:
        self.bound.append(kwargs)
        return self

    async def ainvoke(
        self, _messages: LanguageModelInput, _config: RunnableConfig | None = None
    ) -> BaseMessage:
        self.calls += 1
        await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return AIMessage(content=self.answers[min(self.calls, len(self.answers)) - 1])


def _fitter(
    primary: _Model, fallback: _Model | None, window: float = _WINDOW
) -> LlmCopyBudgetFitter:
    return LlmCopyBudgetFitter(
        LlmCopyBudgetConfig(
            llm=cast(BaseChatModel, primary),
            fallback=cast(Runnable[LanguageModelInput, BaseMessage] | None, fallback),
            primary_seconds=window,
        )
    )


def _command(fitter: LlmCopyBudgetFitter) -> BudgetFitCommand:
    slide = content_slide(3, pt_body=_LONG_PT, en_body=EN_SENTENCES[0])
    return BudgetFitCommand(
        slides=[slide], fitter=fitter, policy_version=POLICY_V4, project_id="p"
    )


def _pt_body(slides: list[dict[str, object]]) -> object:
    return cast(dict[str, object], slides[0]["presentation_pt"])["body"]


def _request() -> FitRequest:
    return FitRequest(targets=(), style_guide="")


@pytest.mark.unit
@pytest.mark.asyncio
class TestFitReachesTheFallback:
    async def test_the_fit_lands_a_rewrite(self) -> None:
        """Scenario: The fit lands a rewrite."""
        primary = _Model(answers=[_fixes(_PRIMARY_TEXT)])
        fallback = _Model(answers=[_fixes(_FALLBACK_TEXT)])

        outcome = await fit_slides_to_budgets(_command(_fitter(primary, fallback)))

        assert _pt_body(outcome.slides) == _PRIMARY_TEXT
        assert outcome.accepted == 1 and outcome.attempts == 1
        assert fallback.calls == 0

    async def test_slow_primary_falls_back_inside_the_budget(self) -> None:
        """Scenario: The primary model is slow and the fallback answers."""
        primary = _Model(answers=[_fixes(_PRIMARY_TEXT)], delay=_SLOW)
        fallback = _Model(answers=[_fixes(_FALLBACK_TEXT)])

        with capture_logs() as logs:
            outcome = await asyncio.wait_for(
                fit_slides_to_budgets(_command(_fitter(primary, fallback))), _SLOW / 2
            )

        assert _pt_body(outcome.slides) == _FALLBACK_TEXT
        assert outcome.accepted == 1 and primary.calls == 1 and fallback.calls == 1
        used = [
            log for log in logs if log["event"] == LOG_COPY_BUDGET_FIT_FALLBACK_USED
        ]
        assert used == [
            {
                "event": LOG_COPY_BUDGET_FIT_FALLBACK_USED,
                "reason": "TimeoutError",
                "log_level": "warning",
            }
        ]
        assert fallback.bound == primary.bound != []

    async def test_fallback_answer_keeps_the_attempts_going(self) -> None:
        """Scenario: The fallback answer keeps the attempts going."""
        primary = _Model(answers=[_fixes(_PRIMARY_TEXT)], delay=_SLOW)
        fallback = _Model(answers=[_fixes(_STILL_LONG_PT), _fixes(_FALLBACK_TEXT)])

        outcome = await fit_slides_to_budgets(_command(_fitter(primary, fallback)))

        assert outcome.attempts == 2 and outcome.asked == 2
        assert fallback.calls == 2 and primary.calls == 2
        assert _pt_body(outcome.slides) == _FALLBACK_TEXT
        assert outcome.still_over == 0

    async def test_both_models_fail_and_the_copy_is_kept(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Both models fail and the copy is kept and logged."""
        monkeypatch.setattr(copy_budget_fit, "COPY_BUDGET_FIT_TIMEOUT_SECONDS", 0.2)
        primary = _Model(answers=[_fixes(_PRIMARY_TEXT)], delay=_SLOW)
        fallback = _Model(answers=[_fixes(_FALLBACK_TEXT)], delay=_SLOW)
        command = _command(_fitter(primary, fallback))

        with capture_logs() as logs:
            outcome = await fit_slides_to_budgets(command)

        assert outcome.slides == command.slides
        assert outcome.attempts == 1 and outcome.accepted == 0
        assert outcome.still_over == 1 and fallback.calls == 1
        failed = [
            log for log in logs if log["event"] == LOG_COPY_BUDGET_FIT_MODEL_FAILED
        ]
        assert [log["error"] for log in failed] == ["TimeoutError"]


@pytest.mark.unit
@pytest.mark.asyncio
class TestFitterFallbackRules:
    async def test_unparseable_primary_answer_goes_to_the_fallback(self) -> None:
        """Scenario: An unparseable primary answer goes to the fallback."""
        primary = _Model(answers=["not json at all"])
        fallback = _Model(answers=[_fixes(_FALLBACK_TEXT)])

        with capture_logs() as logs:
            texts = await _fitter(primary, fallback).fit(_request())

        assert texts == {_FIELD_ID: _FALLBACK_TEXT}
        assert [log["reason"] for log in logs] == ["TypeError"]

    async def test_other_primary_failure_is_not_repeated(self) -> None:
        """Scenario: Any other primary failure is not repeated on the fallback."""
        primary = _Model(error=RuntimeError("all models unavailable"))
        fallback = _Model(answers=[_fixes(_FALLBACK_TEXT)])

        with pytest.raises(RuntimeError):
            await _fitter(primary, fallback).fit(_request())

        assert fallback.calls == 0

    async def test_unparseable_answer_without_a_fallback_is_raised(self) -> None:
        """Scenario: Both models fail and the copy is kept and logged (no fallback, bad JSON)."""
        primary = _Model(answers=["not json at all"])

        with pytest.raises(TypeError):
            await _fitter(primary, None).fit(_request())

    async def test_without_a_fallback_the_primary_keeps_the_budget(self) -> None:
        """Scenario: Without a fallback the primary keeps the whole budget."""
        primary = _Model(answers=[_fixes(_PRIMARY_TEXT)], delay=_WINDOW * 3)

        texts = await _fitter(primary, None).fit(_request())

        assert texts == {_FIELD_ID: _PRIMARY_TEXT}


@pytest.mark.unit
class TestFitBudgetAndPrompt:
    def test_primary_window_leaves_the_fallback_room_inside_the_budget(self) -> None:
        """Scenario: The primary model is slow and the fallback answers (budget split)."""
        assert COPY_BUDGET_FIT_TIMEOUT_SECONDS == 180.0
        assert COPY_BUDGET_FIT_PRIMARY_SECONDS == 120.0
        default = LlmCopyBudgetConfig(llm=cast(BaseChatModel, _Model()))
        assert default.primary_seconds == COPY_BUDGET_FIT_PRIMARY_SECONDS
        assert default.fallback is None

    def test_fit_prompt_does_not_cap_reasoning_at_4096(self) -> None:
        """Scenario: The fit prompt does not cap a reasoning model at 4096 tokens."""
        variables: dict[str, object] = {"fields_json": "[]", "style_guide": ""}
        _, current = render_fit_prompt(FitRequest(()))
        v1_text, v1 = render_prompt(
            COPY_BUDGET_PROMPT_DOMAIN, COPY_BUDGET_PROMPT_FIT, variables, version="v1"
        )
        v3_text, _ = render_prompt(
            COPY_BUDGET_PROMPT_DOMAIN, COPY_BUDGET_PROMPT_FIT, variables, version="v3"
        )

        assert COPY_BUDGET_PROMPT_VERSION == "v3"
        assert current == {"temperature": 0.3, "max_tokens": 32000}
        assert v1 == {"temperature": 0.3, "max_tokens": 4096}
        assert v3_text == v1_text

    def test_orchestrator_gives_the_fitter_the_fast_fallback(self) -> None:
        """Scenario: The primary model is slow and the fallback answers (wiring)."""
        fast = MagicMock()
        fallback_model = MagicMock()
        fast.as_fallback = MagicMock(return_value=fallback_model)

        orchestrator = orchestrator_module.CarouselEditorialOrchestrator(fast)
        fitter = orchestrator._artifact_runner._budget_fitter

        assert isinstance(fitter, LlmCopyBudgetFitter)
        assert fitter._config.fallback is fallback_model
        assert fitter._config.llm is fast
