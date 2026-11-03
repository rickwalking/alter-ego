"""The copy-budget fit leaves the fast model room to answer.

Gherkin: tests/features/copy_budget_fit_token_budget_ae0607.feature.
The fit runs on the real fitter (prompt, bind, parse) and the real validator;
the chat model is a double, or the real OpenCode Go model behind a mocked
HTTP endpoint when the request body itself is checked.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import cast

import httpx
import pytest
import respx
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from pydantic import SecretStr
from structlog.testing import capture_logs

from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel import copy_budget_fit
from rag_backend.application.services.carousel.copy_budget_fit import (
    BudgetFitCommand,
    fit_slides_to_budgets,
)
from rag_backend.application.services.carousel.copy_budget_fit_llm import (
    EmptyFitAnswerError,
    FitRequest,
    LlmCopyBudgetConfig,
    LlmCopyBudgetFitter,
    render_fit_prompt,
)
from rag_backend.domain.constants.copy_budget_fit import (
    COPY_BUDGET_PROMPT_DOMAIN,
    COPY_BUDGET_PROMPT_FIT,
    COPY_BUDGET_PROMPT_VERSION,
    LOG_COPY_BUDGET_FIT_MODEL_FAILED,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.chat_model_factory import build_chat_model
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
_ANSWER = PT_ANSWERS[0]
_BASE_URL = "http://opencode.test/v1"
_REASONING_TOKENS = 4096


def _fixes(text: str) -> str:
    return json.dumps({"fixes": [{"id": _FIELD_ID, "text": text}]}, ensure_ascii=False)


def _all_reasoning() -> AIMessage:
    """What the endpoint returned in prod: no content, the whole cap spent reasoning."""
    return AIMessage(
        content="",
        response_metadata={"finish_reason": "length"},
        usage_metadata={
            "input_tokens": 2797,
            "output_tokens": _REASONING_TOKENS,
            "total_tokens": 2797 + _REASONING_TOKENS,
            "output_token_details": {"reasoning": _REASONING_TOKENS},
        },
    )


@dataclass
class _Model:
    """A chat model double: waits ``delay`` seconds, then answers ``answer``."""

    answer: AIMessage = field(default_factory=lambda: AIMessage(content=""))
    delay: float = 0.0
    calls: int = 0

    def bind(self, **_kwargs: object) -> _Model:
        return self

    async def ainvoke(
        self, _messages: LanguageModelInput, _config: RunnableConfig | None = None
    ) -> BaseMessage:
        self.calls += 1
        await asyncio.sleep(self.delay)
        return self.answer


def _command(model: _Model) -> BudgetFitCommand:
    fitter = LlmCopyBudgetFitter(LlmCopyBudgetConfig(llm=cast(BaseChatModel, model)))
    slide = content_slide(3, pt_body=_LONG_PT, en_body=EN_SENTENCES[0])
    return BudgetFitCommand(
        slides=[slide], fitter=fitter, policy_version=POLICY_V4, project_id="p"
    )


def _pt_body(slides: list[dict[str, object]]) -> object:
    return cast(dict[str, object], slides[0]["presentation_pt"])["body"]


def _failures(logs: list[dict[str, object]]) -> list[object]:
    return [
        log["error"] for log in logs if log["event"] == LOG_COPY_BUDGET_FIT_MODEL_FAILED
    ]


def _sse(content: str) -> str:
    chunk = {
        "id": "c1",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "deepseek-v4.1-flash",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": None,
            }
        ],
    }
    done = {**chunk, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
    return f"data: {json.dumps(chunk)}\n\ndata: {json.dumps(done)}\n\ndata: [DONE]\n\n"


@pytest.mark.unit
@pytest.mark.asyncio
class TestFitAnswers:
    async def test_the_fit_lands_a_rewrite(self) -> None:
        """Scenario: The fit lands a rewrite."""
        model = _Model(answer=AIMessage(content=_fixes(_ANSWER)))

        outcome = await fit_slides_to_budgets(_command(model))

        assert _pt_body(outcome.slides) == _ANSWER
        assert outcome.accepted == 1 and outcome.attempts == 1

    async def test_all_reasoning_empty_answer_is_a_model_failure(self) -> None:
        """Scenario: An all-reasoning empty answer is a model failure."""
        model = _Model(answer=_all_reasoning())
        command = _command(model)

        with capture_logs() as logs:
            outcome = await fit_slides_to_budgets(command)

        assert outcome.slides == command.slides
        assert outcome.attempts == 1 and outcome.accepted == 0
        assert outcome.still_over == 1 and model.calls == 1
        assert _failures(logs) == [EmptyFitAnswerError.__name__]

    async def test_whitespace_only_answer_raises_the_named_error(self) -> None:
        """Scenario: An all-reasoning empty answer is a model failure (whitespace)."""
        fitter = _command(_Model(answer=AIMessage(content=" \n "))).fitter

        with pytest.raises(EmptyFitAnswerError):
            await fitter.fit(FitRequest(targets=()))

    async def test_timeout_is_not_asked_a_second_time(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: A model that times out is not asked a second time."""
        monkeypatch.setattr(copy_budget_fit, "COPY_BUDGET_FIT_TIMEOUT_SECONDS", 0.2)
        render_fit_prompt(FitRequest(targets=()))
        model = _Model(answer=AIMessage(content=_fixes(_ANSWER)), delay=5.0)
        command = _command(model)

        with capture_logs() as logs:
            outcome = await fit_slides_to_budgets(command)

        assert outcome.slides == command.slides
        assert outcome.attempts == 1 and model.calls == 1
        assert _failures(logs) == ["TimeoutError"]


@pytest.mark.unit
class TestFitTokenBudget:
    def test_fit_prompt_does_not_cap_reasoning_at_4096(self) -> None:
        """Scenario: The fit prompt does not cap a reasoning model at 4096 tokens."""
        variables: dict[str, object] = {"fields_json": "[]", "style_guide": ""}
        _, current = render_fit_prompt(FitRequest(targets=()))
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

    @pytest.mark.asyncio
    async def test_provider_receives_the_prompt_token_budget(self) -> None:
        """Scenario: The provider receives the fit prompt's token budget."""
        settings = Settings(
            llm_provider="glm",
            glm_api_key=SecretStr("glm-key"),
            glm_base_url=_BASE_URL,
        )
        fitter = LlmCopyBudgetFitter(
            LlmCopyBudgetConfig(llm=build_chat_model(settings))
        )

        with respx.mock(assert_all_called=True) as router:
            route = router.post(f"{_BASE_URL}/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    text=_sse(_fixes(_ANSWER)),
                    headers={"content-type": "text/event-stream"},
                )
            )
            texts = await fitter.fit(FitRequest(targets=()))

        body = json.loads(route.calls.last.request.content)
        assert texts == {_FIELD_ID: _ANSWER}
        assert body["max_completion_tokens"] == 32000
        assert "max_tokens" not in body
        assert body["temperature"] == 0.3
