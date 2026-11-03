"""The EN slide translation gets the shared JSON retry and the fallback model.

Feature: phase_failure_cause_ae0600.feature
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)
from rag_backend.agents.llm_json_retry import JsonRetryAnswers
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    ERR_EN_TRANSLATION_PARSE_FAILED,
)
from rag_backend.application.services.carousel.editorial_distribution_generation import (
    _generate_en_translations,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    ChatModelRoles,
)
from rag_backend.domain.constants.ai_agents import AGENT_EN_TRANSLATION

_MALFORMED = '{"slides_en": [{"slide_index": 1, "heading": "Cut off'
_VALID = json.dumps({"slides_en": [{"slide_index": 1, "heading": "H", "body": "B"}]})


@dataclass
class _Model:
    """A chat model with a fallback, answering the same text every call."""

    answer: str
    fallback: _Model | None = None
    prompts: list[list[BaseMessage]] = field(default_factory=list)

    async def ainvoke(
        self, messages: list[BaseMessage], config: object = None
    ) -> AIMessage:
        del config
        self.prompts.append(messages)
        return AIMessage(content=self.answer)

    def as_fallback(self) -> _Model | None:
        return self.fallback


def _drafts() -> list[dict[str, object]]:
    return [
        {
            "slide_index": 1,
            "slide_type": "intro",
            "title": "Viram o Grok Bot reservar mesa.",
            "draft_text": "A ligação chama atenção.",
        }
    ]


async def _translate(primary: _Model) -> dict[int, dict[str, object]]:
    """The translation as the orchestrator wires it: through ``JsonRetryAnswers``."""
    model = cast(BaseChatModel, primary)
    return await _generate_en_translations(
        model, _drafts(), JsonRetryAnswers(model, AGENT_EN_TRANSLATION)
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestEnTranslationFallback:
    async def test_malformed_answer_moves_to_the_fallback_model(self) -> None:
        # Scenario: A malformed EN translation is retried on the fallback model
        fallback = _Model(_VALID)
        primary = _Model(_MALFORMED, fallback=fallback)

        translations = await _translate(primary)

        assert fallback.prompts
        assert len(primary.prompts) > 1
        assert translations[1]["heading"] == "H"
        assert translations[1]["body"] == "B"
        first = fallback.prompts[0][0]
        assert isinstance(first, HumanMessage)
        assert "Viram o Grok Bot reservar mesa." in str(first.content)

    async def test_never_parsing_still_raises_its_own_code(self) -> None:
        # Scenario: An EN translation that never parses still fails with its own code
        primary = _Model(_MALFORMED, fallback=_Model(_MALFORMED))

        with pytest.raises(ValueError, match=ERR_EN_TRANSLATION_PARSE_FAILED):
            await _translate(primary)

    async def test_wrong_shape_still_raises_its_own_code(self) -> None:
        # Scenario: An EN translation that never parses still fails with its own code
        wrong = json.dumps({"slides_en": "not a list"})
        primary = _Model(wrong, fallback=_Model(wrong))

        with pytest.raises(ValueError, match=ERR_EN_TRANSLATION_PARSE_FAILED):
            await _translate(primary)

    async def test_a_json_list_answer_still_raises_its_own_code(self) -> None:
        # Scenario: An EN translation that never parses still fails with its own code
        primary = _Model("[1, 2]", fallback=None)

        with pytest.raises(ValueError, match=ERR_EN_TRANSLATION_PARSE_FAILED):
            await _translate(primary)


@pytest.mark.unit
@pytest.mark.asyncio
class TestPlainTranslationWithoutInjection:
    async def test_without_a_retrying_caller_one_plain_call_is_made(self) -> None:
        # Scenario: An EN translation that never parses still fails with its own code
        primary = _Model(_MALFORMED, fallback=_Model(_VALID))

        with pytest.raises(ValueError, match=ERR_EN_TRANSLATION_PARSE_FAILED):
            await _generate_en_translations(cast(BaseChatModel, primary), _drafts())

        assert len(primary.prompts) == 1


@pytest.mark.unit
class TestOrchestratorInjectsTheRetryingCaller:
    def test_runner_gets_json_retry_answers_on_the_fast_model(self) -> None:
        # Scenario: A malformed EN translation is retried on the fallback model
        fast = cast(BaseChatModel, _Model(_VALID))
        reasoning = cast(BaseChatModel, _Model(_VALID))
        orchestrator = CarouselEditorialOrchestrator(
            ChatModelRoles(reasoning=reasoning, fast=fast)
        )

        answers = orchestrator._artifact_runner._translation_answers
        assert isinstance(answers, JsonRetryAnswers)
        assert answers.runnable is fast
        assert answers.agent == AGENT_EN_TRANSLATION
