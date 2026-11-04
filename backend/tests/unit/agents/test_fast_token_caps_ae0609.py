"""Fast-role calls leave the reasoning model room to answer.

Gherkin: tests/features/fast_role_token_caps_ae0609.feature
The cover-ideas and palette completions run on the real routing: the OpenCode Go
chat model behind a mocked HTTP endpoint when the request body is checked, and
the role's queue or routed model over recording fakes otherwise.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID

import httpx
import pytest
import respx
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import SecretStr
from structlog.testing import capture_logs

from rag_backend import monitoring_langfuse
from rag_backend.agents.cover_prompt_prompts import (
    CoverIdeasCompletion,
    EmptyIdeasAnswerError,
    cover_ideas_prompt,
    cover_ideas_trace,
)
from rag_backend.agents.outline_agent import OutlineAgent
from rag_backend.agents.palette_prompts import (
    EmptyPaletteAnswerError,
    PaletteCompletion,
    palette_generation_prompt,
    palette_generation_trace,
)
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.cover_prompt_ideas_service import (
    CoverIdeasPorts,
    CoverIdeasRequest,
    CoverPromptIdeasError,
    CoverPromptIdeasService,
)
from rag_backend.application.services.carousel.palette_generation_service import (
    PaletteGenerationError,
    PaletteGenerationPorts,
    PaletteGenerationRequest,
    PaletteGenerationService,
)
from rag_backend.domain.constants.cover_prompt_ideas import (
    IDEA_ATTEMPTS,
    LOG_COVER_IDEAS_CALL_FAILED,
    IdeaLocale,
)
from rag_backend.domain.constants.palette_generation import LOG_PALETTE_CALL_FAILED
from rag_backend.domain.constants.pov_prompts import (
    RADAR_PROMPT_DOMAIN,
    RADAR_PROMPT_OUTLINE,
    RADAR_PROMPT_VERSION,
)
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.config.llm_routing_constants import LLM_ROLE_FAST
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external import model_queue_chat_model as queue_module
from rag_backend.infrastructure.external.chat_model_factory import build_chat_model
from rag_backend.infrastructure.external.model_queue_chat_model import (
    ModelQueueChatModel,
)
from rag_backend.infrastructure.external.routed_chat_model import RoutedChatModel
from rag_backend.infrastructure.llm.model_breaker import (
    BreakerPolicy,
    BreakerRegistry,
)
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_BASE_URL = "http://opencode.test/v1"
_MODEL_FAST = "deepseek-v4.1-flash"
_MODEL_NEXT = "qwen3.8-flash"
_MODEL_MAX_TOKENS = 32000
_YAML_OUTLINE_CAP = 2048
_ANSWER = '{"ok": true}'
_PROMPT = "the prompt"
_CONTENT_ROLLS = 3

Complete = Callable[[BaseChatModel], Awaitable[str]]


async def _cover(model: BaseChatModel) -> str:
    return await CoverIdeasCompletion(model).complete(_PROMPT)


async def _palette(model: BaseChatModel) -> str:
    return await PaletteCompletion(model).complete(_PROMPT)


_CALLS = [pytest.param(_cover, id="cover ideas"), pytest.param(_palette, id="palette")]


def _sse(content: str) -> str:
    chunk = {
        "id": "c1",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": _MODEL_FAST,
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


def _prod_fast_model() -> BaseChatModel:
    """The fast role as prod builds it: the queue of two OpenCode Go models."""
    settings = Settings(
        llm_provider="glm",
        glm_api_key=SecretStr("glm-key"),
        glm_base_url=_BASE_URL,
        llm_model_queue_fast=f"go:{_MODEL_FAST},go:{_MODEL_NEXT}",
    )
    return build_chat_model(settings, LLM_ROLE_FAST)


def _mock_endpoint(router: respx.MockRouter, content: str) -> respx.Route:
    return router.post(f"{_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=_sse(content),
            headers={"content-type": "text/event-stream"},
        )
    )


def _empty_then_answer(log: CallLog) -> ModelQueueChatModel:
    """A queue whose first model answers nothing and whose next model answers."""
    return ModelQueueChatModel(
        models=[
            FakeChat(model_name=_MODEL_FAST, reply=lambda _prompt: "", log=log),
            FakeChat(model_name=_MODEL_NEXT, reply=lambda _prompt: _ANSWER, log=log),
        ],
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
        registry=BreakerRegistry(policy=BreakerPolicy()),
    )


def _always_empty(reply: str = "") -> RoutedChatModel:
    """A routed model with no fallback left: its empty answer reaches the caller."""
    return RoutedChatModel(
        primary=FakeChat(reply=lambda _prompt: reply),
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
        attempts=1,
    )


def _failed_calls(logs: list[dict[str, object]], event: str) -> list[object]:
    return [log["error"] for log in logs if log["event"] == event]


@dataclass
class _Generations(BaseCallbackHandler):
    """A Langfuse handler double: the tags of each chat-model run it sees."""

    tags: list[list[str]] = field(default_factory=list)

    def on_chat_model_start(
        self,
        serialized: dict[str, object],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: object,
    ) -> None:
        tags = kwargs.get("tags")
        self.tags.append(list(tags) if isinstance(tags, list) else [])


@pytest.fixture(autouse=True)
def _no_queue_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _skip(_seconds: float) -> None:
        return None

    monkeypatch.setattr(queue_module, "_sleep", _skip)


@pytest.mark.parametrize("complete", _CALLS)
async def test_the_provider_receives_the_token_budget(complete: Complete) -> None:
    """Scenario: The provider receives the call's token budget."""
    with respx.mock(assert_all_called=True) as router:
        route = _mock_endpoint(router, _ANSWER)
        answer = await complete(_prod_fast_model())

    body = json.loads(route.calls.last.request.content)
    assert answer == _ANSWER
    assert body["max_completion_tokens"] == _MODEL_MAX_TOKENS
    assert "max_tokens" not in body


async def test_an_unbound_yaml_cap_stays_off_the_wire() -> None:
    """Scenario: A prompt YAML's cap that no code binds stays off the wire."""
    _, yaml_model = render_prompt(
        RADAR_PROMPT_DOMAIN,
        RADAR_PROMPT_OUTLINE,
        {"roles": [], "slide_count": 1},
        version=RADAR_PROMPT_VERSION,
    )
    outline = [{"slide_index": 1, "title": "Hook", "key_points": ["Open strong"]}]
    get_ai_response_cache().clear()

    with respx.mock(assert_all_called=True) as router:
        route = _mock_endpoint(router, json.dumps(outline))
        agent = OutlineAgent(llm=_prod_fast_model())
        await agent.generate_outline("Topic", "Devs", "Brief", ["Source"])

    body = json.loads(route.calls.last.request.content)
    assert yaml_model["max_tokens"] == _YAML_OUTLINE_CAP
    assert body["max_completion_tokens"] == _MODEL_MAX_TOKENS


@pytest.mark.parametrize("complete", _CALLS)
async def test_an_empty_primary_answer_moves_to_the_fallback(
    complete: Complete,
) -> None:
    """Scenario: An empty primary answer moves the call to the fallback."""
    log = CallLog()

    answer = await complete(_empty_then_answer(log))

    assert answer == _ANSWER
    assert log.models == [_MODEL_FAST] * _CONTENT_ROLLS + [_MODEL_NEXT]
    budgets = [kwargs["max_tokens"] for kwargs in log.kwargs]
    assert budgets == [_MODEL_MAX_TOKENS] * len(log.models)


async def test_an_empty_cover_ideas_answer_is_a_logged_failure() -> None:
    """Scenario: An empty cover ideas answer is a logged model failure."""
    service = CoverPromptIdeasService(
        CoverIdeasPorts(
            llm=CoverIdeasCompletion(_always_empty()),
            render_prompt=cover_ideas_prompt,
            trace=cover_ideas_trace,
        )
    )
    request = CoverIdeasRequest(
        topic="IA no trabalho", palette=None, locale=IdeaLocale.PT, user_id="owner"
    )

    with capture_logs() as logs, pytest.raises(CoverPromptIdeasError):
        await service.suggest(request)

    named = _failed_calls(logs, LOG_COVER_IDEAS_CALL_FAILED)
    assert named == [EmptyIdeasAnswerError.__name__] * IDEA_ATTEMPTS


async def test_an_empty_palette_answer_is_a_logged_failure() -> None:
    """Scenario: An empty palette answer is a logged model failure."""
    service = PaletteGenerationService(
        PaletteGenerationPorts(
            llm=PaletteCompletion(_always_empty()),
            render_prompt=palette_generation_prompt,
            trace=palette_generation_trace,
        )
    )
    request = PaletteGenerationRequest(description="Azul noturno", user_id="owner")

    with capture_logs() as logs, pytest.raises(PaletteGenerationError):
        await service.generate(request)

    named = _failed_calls(logs, LOG_PALETTE_CALL_FAILED)
    assert named == [EmptyPaletteAnswerError.__name__]


async def test_a_failed_palette_call_is_logged_with_its_error() -> None:
    """Scenario: A failed palette call is logged with its error."""
    failing = RoutedChatModel(
        primary=FakeChat(error=ConnectionError("down")),
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
        attempts=1,
    )
    service = PaletteGenerationService(
        PaletteGenerationPorts(
            llm=PaletteCompletion(failing),
            render_prompt=palette_generation_prompt,
            trace=palette_generation_trace,
        )
    )
    request = PaletteGenerationRequest(description="Azul noturno", user_id="owner")

    with capture_logs() as logs, pytest.raises(PaletteGenerationError):
        await service.generate(request)

    assert _failed_calls(logs, LOG_PALETTE_CALL_FAILED) == [ConnectionError.__name__]


@pytest.mark.parametrize(
    ("complete", "error"),
    [
        pytest.param(_cover, EmptyIdeasAnswerError, id="cover ideas"),
        pytest.param(_palette, EmptyPaletteAnswerError, id="palette"),
    ],
)
async def test_a_whitespace_answer_counts_as_empty(
    complete: Complete, error: type[Exception]
) -> None:
    """Scenario: A whitespace answer counts as empty."""
    with pytest.raises(error):
        await complete(_always_empty(" \n "))


@pytest.mark.parametrize("complete", _CALLS)
async def test_the_call_reaches_langfuse_as_a_generation(
    complete: Complete, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: The call reaches Langfuse as a generation."""
    generations = _Generations()
    monkeypatch.setattr(monitoring_langfuse, "_langfuse_handler", generations)
    log = CallLog()
    routed = RoutedChatModel(
        primary=FakeChat(reply=lambda _prompt: _ANSWER, log=log),
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
        attempts=1,
    )

    await complete(routed)

    assert [tag for tags in generations.tags for tag in tags if "model:" in tag] == [
        "model:fake-model"
    ]
