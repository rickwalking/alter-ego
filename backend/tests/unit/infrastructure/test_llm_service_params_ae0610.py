"""LLMService sends the requested temperature and records its calls.

Gherkin: tests/features/llm_service_params_ae0610.feature
The chat models are the real ones the factory builds, behind a mocked HTTP
endpoint, so the assertions read the request body the provider would receive.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from uuid import UUID

import httpx
import pytest
import respx
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from pydantic import SecretStr

from rag_backend import monitoring_langfuse
from rag_backend.domain.protocols import LlmCallTrace
from rag_backend.infrastructure.config.llm_routing_constants import LLM_ROLE_FAST
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external import routed_chat_model
from rag_backend.infrastructure.external.anthropic_llm import AnthropicLLMService
from rag_backend.infrastructure.external.routed_chat_model import (
    EmptyLLMResponseError,
)
from rag_backend.infrastructure.langfuse_phase_trace import phase_trace
from tests.langfuse_trace_fakes import install_trace_collector

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_BASE_URL = "http://opencode.test/v1"
_MODEL_FIRST = "deepseek-v4.1-flash"
_MODEL_NEXT = "qwen3.8-flash"
_QUEUE = f"go:{_MODEL_FIRST},go:{_MODEL_NEXT}"
_FACTORY_MAX_TOKENS = 32000
_ANSWER = "the answer"
_MESSAGES = [{"role": "user", "content": "the prompt"}]
_TRACE = LlmCallTrace(
    phase="refine_design",
    agent_name="carousel_refinement",
    content_type="carousel",
    project_id="p-1",
)

Respond = Callable[[str], str]


def _sse(content: str, model: str) -> str:
    chunk = {
        "id": "c1",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": model,
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


def _service(role: str | None = None, queue: str = "") -> AnthropicLLMService:
    settings = Settings(
        llm_provider="glm",
        glm_api_key=SecretStr("glm-key"),
        glm_base_url=_BASE_URL,
        llm_model_queue_fast=queue,
    )
    return AnthropicLLMService(settings, role=role)


def _role_less() -> AnthropicLLMService:
    return _service()


def _fast_queue() -> AnthropicLLMService:
    return _service(LLM_ROLE_FAST, _QUEUE)


def _routed_fast() -> AnthropicLLMService:
    return _service(LLM_ROLE_FAST)


@dataclass
class _Endpoint:
    """The mocked chat endpoint: the bodies it received, the answer per model."""

    respond: Respond
    bodies: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.bodies.append(body)
        model = str(body["model"])
        return httpx.Response(
            200,
            text=_sse(self.respond(model), model),
            headers={"content-type": "text/event-stream"},
        )


def _mount(router: respx.MockRouter, respond: Respond) -> _Endpoint:
    endpoint = _Endpoint(respond)
    router.post(f"{_BASE_URL}/chat/completions").mock(side_effect=endpoint)
    return endpoint


def _always(answer: str) -> Respond:
    return lambda _model: answer


def _only(model: str) -> Respond:
    return lambda asked: _ANSWER if asked == model else ""


@dataclass
class _Generations(BaseCallbackHandler):
    """A Langfuse handler double: the name and tags of each chat-model run."""

    names: list[object] = field(default_factory=list)
    tags: list[list[str]] = field(default_factory=list)

    def on_chat_model_start(
        self,
        serialized: dict[str, object],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: object,
    ) -> None:
        self.names.append(kwargs.get("name"))
        tags = kwargs.get("tags")
        self.tags.append(list(tags) if isinstance(tags, list) else [])


@pytest.fixture
def generations(monkeypatch: pytest.MonkeyPatch) -> _Generations:
    handler = _Generations()
    monkeypatch.setattr(monitoring_langfuse, "_langfuse_handler", handler)
    return handler


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    async def _skip(_seconds: float) -> None:
        return None

    monkeypatch.setattr(routed_chat_model, "_sleep", _skip)
    yield


# Scenario: The provider receives the requested temperature
@pytest.mark.parametrize(
    ("build", "temperature"),
    [
        pytest.param(_role_less, 0.2, id="role-less 0.2"),
        pytest.param(_role_less, 0.3, id="role-less 0.3"),
        pytest.param(_fast_queue, 0.8, id="fast 0.8"),
    ],
)
@respx.mock
async def test_the_provider_receives_the_requested_temperature(
    build: Callable[[], AnthropicLLMService], temperature: float
) -> None:
    endpoint = _mount(respx.mock, _always(_ANSWER))

    answer = await build().generate(_MESSAGES, temperature=temperature)

    assert answer == _ANSWER
    assert endpoint.bodies[0]["temperature"] == temperature
    assert endpoint.bodies[0]["max_completion_tokens"] == _FACTORY_MAX_TOKENS


# Scenario: A caller that names no temperature sends the default
@respx.mock
async def test_no_temperature_sends_the_default() -> None:
    endpoint = _mount(respx.mock, _always(_ANSWER))

    await _fast_queue().generate(_MESSAGES)

    assert endpoint.bodies[0]["temperature"] == pytest.approx(0.7)


# Scenario: A streamed call receives the requested temperature
@respx.mock
async def test_a_streamed_call_receives_the_requested_temperature(
    generations: _Generations,
) -> None:
    endpoint = _mount(respx.mock, _always(_ANSWER))

    chunks = [
        chunk
        async for chunk in _role_less().generate_stream(_MESSAGES, temperature=0.3)
    ]

    assert "".join(chunks) == _ANSWER
    assert endpoint.bodies[0]["temperature"] == pytest.approx(0.3)
    assert len(generations.names) == 1


# Scenario: A caller cannot set a token cap
@respx.mock
async def test_a_caller_cannot_set_a_token_cap() -> None:
    endpoint = _mount(respx.mock, _always(_ANSWER))
    capped: dict[str, int] = {"max_tokens": 777}

    with pytest.raises(TypeError):
        await _role_less().generate(_MESSAGES, **capped)

    assert endpoint.bodies == []


# Scenario: An empty answer moves the call down the fast queue
@respx.mock
async def test_an_empty_answer_moves_down_the_fast_queue() -> None:
    endpoint = _mount(respx.mock, _only(_MODEL_NEXT))

    answer = await _fast_queue().generate(_MESSAGES, temperature=0.2)

    assert answer == _ANSWER
    assert {body["model"] for body in endpoint.bodies} == {_MODEL_FIRST, _MODEL_NEXT}
    assert {body["temperature"] for body in endpoint.bodies} == {0.2}
    assert {body["max_completion_tokens"] for body in endpoint.bodies} == {
        _FACTORY_MAX_TOKENS
    }


# Scenario: An empty answer moves the routed call to its fallback
@respx.mock
async def test_an_empty_answer_moves_the_routed_call_to_its_fallback() -> None:
    endpoint = _mount(respx.mock, _only(_MODEL_NEXT))

    answer = await _routed_fast().generate(_MESSAGES, temperature=0.2)

    assert answer == _ANSWER
    assert endpoint.bodies[-1]["model"] == _MODEL_NEXT
    assert endpoint.bodies[-1]["temperature"] == pytest.approx(0.2)


# Scenario: An empty answer from the last routed model is a model failure
@respx.mock
async def test_an_empty_answer_from_the_last_routed_model_is_a_failure() -> None:
    endpoint = _mount(respx.mock, _always(""))

    with pytest.raises(EmptyLLMResponseError):
        await _routed_fast().generate(_MESSAGES)

    assert endpoint.bodies[-1]["model"] == _MODEL_NEXT


# Scenario: An empty answer with no fallback is a model failure
@pytest.mark.parametrize("answer", ["", " \n "], ids=["nothing", "blank"])
@respx.mock
async def test_an_empty_answer_with_no_fallback_is_a_failure(answer: str) -> None:
    _mount(respx.mock, _always(answer))

    with pytest.raises(EmptyLLMResponseError):
        await _role_less().generate(_MESSAGES)


# Scenario: The call reaches Langfuse as a generation
@respx.mock
async def test_the_call_reaches_langfuse_as_a_generation(
    generations: _Generations,
) -> None:
    _mount(respx.mock, _always(_ANSWER))

    with phase_trace({"phase": "ai_suggest", "content_type": "blog_post"}):
        await _fast_queue().generate(_MESSAGES)

    assert generations.names == ["blog_post.ai_suggest"]
    assert f"model:{_MODEL_FIRST}" in generations.tags[0]


# Scenario: Without Langfuse the call runs with no callbacks
@respx.mock
async def test_without_langfuse_the_call_runs_with_no_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(monitoring_langfuse, "get_langfuse_handler", lambda: None)
    _mount(respx.mock, _always(_ANSWER))

    assert await _role_less().generate(_MESSAGES) == _ANSWER


# Scenario: The service opens the phase the call names
@respx.mock
async def test_the_service_opens_the_phase_the_call_names(
    generations: _Generations, monkeypatch: pytest.MonkeyPatch
) -> None:
    collector = install_trace_collector(monkeypatch)
    _mount(respx.mock, _always(_ANSWER))

    await _role_less().generate(_MESSAGES, trace=_TRACE)

    assert generations.names == ["carousel.refine_design"]
    metadata = collector.traces[0].span_metadata
    assert metadata["phase"] == "refine_design"
    assert metadata["agent_name"] == "carousel_refinement"
    assert metadata["content_type"] == "carousel"
    assert metadata["project_id"] == "p-1"


# Scenario: A failing call closes the phase it named
@respx.mock
async def test_a_failing_call_closes_the_phase_it_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = install_trace_collector(monkeypatch)
    _mount(respx.mock, _always(""))

    with pytest.raises(EmptyLLMResponseError):
        await _role_less().generate(_MESSAGES, trace=_TRACE)

    output = collector.traces[0].output
    assert isinstance(output, dict)
    assert output["status"] == "error"
    assert output["error_type"] == "EmptyLLMResponseError"
