"""AE-0391: per-role model routing and the automatic GLM fallback.

Scenarios: see tests/features/llm_model_routing_ae0391.feature
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.editorial_workflow_types import (
    ChatModelRoles,
)
from rag_backend.infrastructure.config.llm_routing_constants import (
    DEFAULT_CONTENT_DRAFT_CONCURRENCY,
    LLM_ROLE_FAST,
    LLM_ROLE_REASONING,
    LLM_TAG_FALLBACK,
    LLM_TIMEOUT_FALLBACK_SECONDS,
    LOG_LLM_FALLBACK_USED,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external import routed_chat_model as routed_module
from rag_backend.infrastructure.external.anthropic_llm import AnthropicLLMService
from rag_backend.infrastructure.external.chat_model_factory import (
    build_chat_model,
    build_role_models,
)
from rag_backend.infrastructure.external.routed_chat_model import (
    RoutedChatModel,
    fallback_runnable_for,
    model_id_of,
)
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat, StatusError

PROMPT = [HumanMessage(content="hello")]


def _settings(**overrides: object) -> Settings:
    base = Settings(
        anthropic_api_key=SecretStr("anthropic-key"),
        llm_provider="glm",
        glm_api_key=SecretStr("glm-key"),
    )
    return base.model_copy(update=overrides)


def _routed(primary: FakeChat, fallback: FakeChat | None) -> RoutedChatModel:
    return RoutedChatModel(
        primary=primary, fallback=fallback, role=LLM_ROLE_FAST, timeout_seconds=5.0
    )


# --- Routing -----------------------------------------------------------------


def test_reasoning_role_routes_to_reasoning_model_with_glm_fallback() -> None:
    # Scenario: the reasoning role uses the reasoning model
    model = build_chat_model(_settings(), LLM_ROLE_REASONING)

    assert isinstance(model, RoutedChatModel)
    assert isinstance(model.primary, ChatOpenAI)
    assert model.primary.model_name == "deepseek-v4-pro"
    assert model.primary.openai_api_base == "https://opencode.ai/zen/go/v1"
    assert model.timeout_seconds == 240.0
    assert isinstance(model.fallback, ChatOpenAI)
    assert model.fallback.model_name == "glm-5.3"
    assert model.role == LLM_ROLE_REASONING


def test_fast_role_routes_to_fast_model() -> None:
    # Scenario: the fast role uses the fast model
    model = build_chat_model(_settings(), LLM_ROLE_FAST)

    assert isinstance(model, RoutedChatModel)
    assert model.model_name == "deepseek-v4.1-flash"
    assert model.timeout_seconds == 120.0


def test_role_model_ids_come_from_settings() -> None:
    # Scenario: model ids come from settings, not code
    model = build_chat_model(
        _settings(llm_model_fast="glm-5.3-flash", llm_model_fallback="glm-x"),
        LLM_ROLE_FAST,
    )

    assert isinstance(model, RoutedChatModel)
    assert model.model_name == "glm-5.3-flash"
    assert model.fallback is not None
    assert model_id_of(model.fallback) == "glm-x"


def test_role_models_carry_the_opencode_session_header() -> None:
    # AE-0330 still holds for the DeepSeek models on the same endpoint.
    model = build_chat_model(_settings(), LLM_ROLE_FAST)

    assert isinstance(model, RoutedChatModel)
    assert isinstance(model.primary, ChatOpenAI)
    headers = model.primary.default_headers or {}
    assert "x-opencode-session" in headers


def test_unknown_role_uses_glm_model_and_reasoning_budget() -> None:
    model = build_chat_model(_settings(), "other")

    assert isinstance(model, RoutedChatModel)
    assert model.model_name == "glm-5.3"
    assert model.timeout_seconds == 240.0


def test_no_role_keeps_the_single_glm_chat_model() -> None:
    # Chat / RAG agents are untouched by AE-0391.
    model = build_chat_model(_settings())

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "glm-5.3"


@pytest.mark.parametrize("role", [LLM_ROLE_REASONING, LLM_ROLE_FAST])
def test_anthropic_provider_ignores_roles(role: str) -> None:
    # Scenario: role routing keeps the Anthropic provider semantics
    model = build_chat_model(_settings(llm_provider="anthropic"), role)

    assert isinstance(model, ChatAnthropic)


def test_role_without_glm_key_degrades_to_anthropic() -> None:
    # Scenario: role routing without a GLM key degrades to Anthropic
    model = build_chat_model(_settings(glm_api_key=SecretStr("")), LLM_ROLE_FAST)

    assert isinstance(model, ChatAnthropic)


def test_build_role_models_builds_both_roles() -> None:
    roles = build_role_models(_settings())

    assert model_id_of(roles.reasoning) == "deepseek-v4-pro"
    assert model_id_of(roles.fast) == "deepseek-v4.1-flash"
    assert roles.draft_concurrency == DEFAULT_CONTENT_DRAFT_CONCURRENCY
    assert (
        build_role_models(_settings(content_draft_concurrency=2)).draft_concurrency == 2
    )


def test_llm_service_role_routing_and_cached_role_models() -> None:
    service = AnthropicLLMService(_settings(), role=LLM_ROLE_FAST)

    assert model_id_of(service.chat_model) == "deepseek-v4.1-flash"
    assert service.role_models is service.role_models
    assert model_id_of(service.role_models.reasoning) == "deepseek-v4-pro"


def test_settings_defaults() -> None:
    settings = _settings()

    assert settings.llm_model_reasoning == "deepseek-v4-pro"
    assert settings.llm_model_fast == "deepseek-v4.1-flash"
    assert settings.llm_model_fallback == "glm-5.3"
    assert settings.content_draft_concurrency == DEFAULT_CONTENT_DRAFT_CONCURRENCY


def test_chat_model_roles_coerce() -> None:
    single = FakeChat()
    roles = ChatModelRoles.coerce(single)

    assert roles.reasoning is single
    assert roles.fast is single
    assert ChatModelRoles.coerce(roles) is roles


def test_model_id_of_unknown_model() -> None:
    assert model_id_of(FakeChat(model_name="")) == "unknown"


# --- Fallback ----------------------------------------------------------------


async def test_primary_success_does_not_call_fallback_and_tags_the_run() -> None:
    # Scenario: every generation records its role and model
    log = CallLog()
    model = _routed(
        FakeChat(model_name="primary", log=log),
        FakeChat(model_name="fallback", log=log),
    )

    result = await model.ainvoke(PROMPT)

    assert result.content == "ok"
    assert log.models == ["primary"]
    assert "role:fast" in log.tags[0]
    assert "model:primary" in log.tags[0]
    assert LLM_TAG_FALLBACK not in log.tags[0]


def _failing(status: int) -> Callable[[CallLog], FakeChat]:
    return lambda log: FakeChat(
        model_name="primary", log=log, error=StatusError(status)
    )


def _empty(log: CallLog) -> FakeChat:
    return FakeChat(model_name="primary", log=log, reply=lambda _prompt: "   ")


@pytest.mark.parametrize(
    ("make_primary", "reason"),
    [
        (_failing(503), "error"),
        (_failing(429), "error"),
        (_failing(400), "error"),
        (_empty, "empty_content"),
    ],
)
async def test_fallback_answers_when_primary_fails(
    make_primary: Callable[[CallLog], FakeChat], reason: str
) -> None:
    # Scenario Outline: the fallback model answers when the primary call fails
    log = CallLog()
    model = _routed(
        make_primary(log),
        FakeChat(model_name="fallback", log=log, reply=lambda _p: "from fallback"),
    )

    with capture_logs() as logs:
        result = await model.ainvoke(PROMPT)

    assert result.content == "from fallback"
    assert log.models == ["primary", "fallback"]
    assert LLM_TAG_FALLBACK in log.tags[1]
    assert "model:fallback" in log.tags[1]
    events = [entry for entry in logs if entry["event"] == LOG_LLM_FALLBACK_USED]
    assert len(events) == 1
    assert events[0]["reason"] == reason
    assert events[0]["primary_model"] == "primary"
    assert events[0]["fallback_model"] == "fallback"
    assert events[0]["log_level"] == "warning"


async def test_fallback_answers_on_timeout() -> None:
    # Scenario Outline: ... a timeout
    log = CallLog()
    model = RoutedChatModel(
        primary=FakeChat(model_name="primary", log=log, delay=1.0),
        fallback=FakeChat(model_name="fallback", log=log),
        role=LLM_ROLE_REASONING,
        timeout_seconds=0.01,
    )

    with capture_logs() as logs:
        result = await model.ainvoke(PROMPT)

    assert result.content == "ok"
    assert log.models == ["primary", "fallback"]
    assert [e["reason"] for e in logs if e["event"] == LOG_LLM_FALLBACK_USED] == [
        "timeout"
    ]


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_error_is_raised_without_fallback(status: int) -> None:
    # Scenario: an auth failure is not masked by the fallback
    log = CallLog()
    model = _routed(
        FakeChat(model_name="primary", log=log, error=StatusError(status)),
        FakeChat(model_name="fallback", log=log),
    )

    with pytest.raises(StatusError):
        await model.ainvoke(PROMPT)

    assert log.models == ["primary"]


async def test_no_fallback_reraises_and_keeps_empty_answers() -> None:
    log = CallLog()
    failing = _routed(FakeChat(log=log, error=StatusError(500)), None)
    with pytest.raises(StatusError):
        await failing.ainvoke(PROMPT)

    empty = _routed(FakeChat(reply=lambda _p: ""), None)
    assert (await empty.ainvoke(PROMPT)).content == ""


async def test_fallback_empty_answer_is_returned_as_is() -> None:
    model = _routed(
        FakeChat(model_name="primary", reply=lambda _p: ""),
        FakeChat(model_name="fallback", reply=lambda _p: ""),
    )

    assert (await model.ainvoke(PROMPT)).content == ""


async def test_tool_call_without_content_is_not_empty() -> None:
    message = AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "1"}])

    assert routed_module._is_empty(message) is False
    assert routed_module._is_empty(AIMessage(content="")) is True


async def test_bound_kwargs_reach_the_fallback() -> None:
    log = CallLog()
    model = _routed(
        FakeChat(model_name="primary", log=log, error=StatusError(502)),
        FakeChat(model_name="fallback", log=log),
    )

    await model.bind(temperature=0.2).ainvoke(PROMPT)

    assert log.kwargs[1].get("temperature") == 0.2


async def test_fallback_failure_propagates() -> None:
    model = _routed(
        FakeChat(error=StatusError(500)),
        FakeChat(error=StatusError(502)),
    )

    with pytest.raises(StatusError) as excinfo:
        await model.ainvoke(PROMPT)

    assert excinfo.value.status_code == 502


async def test_sync_generate_uses_primary() -> None:
    log = CallLog()
    model = _routed(FakeChat(model_name="primary", log=log), FakeChat(log=log))

    result = await asyncio.to_thread(model.invoke, PROMPT)

    assert result.content == "ok"
    assert log.models == ["primary"]


def test_as_fallback_and_fallback_runnable_for() -> None:
    fallback = FakeChat(model_name="fallback")
    model = _routed(FakeChat(model_name="primary"), fallback)

    as_fallback = model.as_fallback()
    assert as_fallback is not None
    assert as_fallback.primary is fallback
    assert as_fallback.is_fallback is True
    assert as_fallback.timeout_seconds == LLM_TIMEOUT_FALLBACK_SECONDS
    assert _routed(FakeChat(), None).as_fallback() is None

    assert isinstance(fallback_runnable_for(model), RoutedChatModel)
    assert fallback_runnable_for(model.bind(temperature=0.1)) is not None
    assert fallback_runnable_for(FakeChat()) is None
    assert fallback_runnable_for(FakeChat().bind(temperature=0.1)) is None
    assert (
        fallback_runnable_for(_routed(FakeChat(), None).bind(temperature=0.1)) is None
    )
