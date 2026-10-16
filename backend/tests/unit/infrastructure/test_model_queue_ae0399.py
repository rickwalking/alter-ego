"""Model queue, circuit breaker, OpenCode sidecar and alerts (AE-0399).

Gherkin: tests/features/llm_model_queue_ae0399.feature
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field

import httpx
import pytest
from pydantic import SecretStr

from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
from rag_backend.infrastructure.config.llm_routing_constants import LLM_ROLE_FAST
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external import model_queue_chat_model as queue_module
from rag_backend.infrastructure.external import opencode_sidecar_model as sidecar_module
from rag_backend.infrastructure.external.chat_model_factory import build_chat_model
from rag_backend.infrastructure.external.model_queue_chat_model import (
    AllModelsUnavailableError,
    ModelQueueChatModel,
)
from rag_backend.infrastructure.external.model_queue_factory import queue_spec
from rag_backend.infrastructure.external.opencode_sidecar_model import (
    OpenCodeSidecarChatModel,
    OpenCodeSidecarError,
)
from rag_backend.infrastructure.external.routed_chat_model import RoutedChatModel
from rag_backend.infrastructure.llm.model_breaker import (
    BreakerPolicy,
    BreakerRegistry,
    BreakerState,
    BreakerTransition,
    FailureClass,
    classify_failure,
)
from rag_backend.infrastructure.notifications.llm_alerts import TelegramLlmAlerts
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat

pytestmark = pytest.mark.unit

PROMPT = "Escreva a legenda."


class StatusError(RuntimeError):
    def __init__(
        self, status: int, text: str = "", retry_after: str | None = None
    ) -> None:
        super().__init__(f"status {status} {text}")
        self.status_code = status
        headers = {"retry-after": retry_after} if retry_after else {}
        self.response = httpx.Response(status, headers=headers)


@dataclass
class _Clock:
    now: float = 1000.0

    def __call__(self) -> float:
        return self.now


@dataclass
class _Script:
    """Raises the listed errors in order, then answers ``reply``."""

    errors: list[Exception]
    reply: str = "ok"
    calls: list[int] = field(default_factory=list)

    def __call__(self, _prompt: str) -> str:
        self.calls.append(1)
        if self.errors:
            raise self.errors.pop(0)
        return self.reply


@pytest.fixture(autouse=True)
def _waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    recorded: list[float] = []

    async def _record(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(queue_module, "_sleep", _record)
    return recorded


def _registry(
    clock: _Clock, transitions: list[BreakerTransition] | None = None
) -> BreakerRegistry:
    registry = BreakerRegistry(policy=BreakerPolicy(), clock=clock)
    if transitions is not None:
        registry.subscribe(transitions.append)
    return registry


def _queue(
    replies: list[_Script],
    registry: BreakerRegistry,
    log: CallLog,
    down: list[str] | None = None,
) -> ModelQueueChatModel:
    models = [
        FakeChat(model_name=f"m{i}", log=log, reply=reply)
        for i, reply in enumerate(replies)
    ]
    hook = (lambda role, summary: down.append(summary)) if down is not None else None
    return ModelQueueChatModel(
        models=models,
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
        registry=registry,
        on_all_down=hook,
    )


# Scenario: The first model with a closed breaker answers
async def test_first_model_answers() -> None:
    log = CallLog()
    model = _queue([_Script([]), _Script([]), _Script([])], _registry(_Clock()), log)
    result = await model.ainvoke(PROMPT)
    assert result.content == "ok"
    assert log.models == ["m0"]


# Scenario: A refused model is skipped at once
async def test_fatal_opens_long_and_is_skipped_next_time() -> None:
    log, clock, transitions = CallLog(), _Clock(), []
    first = _Script([StatusError(403, "FreeTierError")] * 5)
    model = _queue(
        [first, _Script([], reply="second")], _registry(clock, transitions), log
    )

    assert (await model.ainvoke(PROMPT)).content == "second"
    assert (await model.ainvoke(PROMPT)).content == "second"

    assert len(first.calls) == 1
    opened = [t for t in transitions if t.new is BreakerState.OPEN]
    assert opened[0].failure is FailureClass.FATAL
    assert opened[0].cooldown == BreakerPolicy().fatal_cooldown


# Scenario: A usage limit opens the breaker without retries
async def test_quota_opens_without_retries(_waits: list[float]) -> None:
    log, transitions = CallLog(), []
    first = _Script([StatusError(429, "GoUsageLimitError weekly")] * 5)
    model = _queue(
        [first, _Script([], reply="fallback")], _registry(_Clock(), transitions), log
    )
    assert (await model.ainvoke(PROMPT)).content == "fallback"
    assert len(first.calls) == 1
    assert _waits == []
    assert transitions[-1].failure is FailureClass.QUOTA


# Scenario: Transient errors retry, then open the breaker
async def test_transient_retries_then_opens(_waits: list[float]) -> None:
    log, transitions = CallLog(), []
    first = _Script([StatusError(503)] * 10)
    model = _queue(
        [first, _Script([], reply="next")], _registry(_Clock(), transitions), log
    )
    assert (await model.ainvoke(PROMPT)).content == "next"
    assert len(first.calls) == 3
    assert len(_waits) == 2
    assert transitions[-1].new is BreakerState.OPEN


# Scenario: A rate limit is debounced with Retry-After
async def test_throttle_waits_retry_after(_waits: list[float]) -> None:
    log = CallLog()
    first = _Script([StatusError(429, "rate limited", retry_after="2")])
    model = _queue([first, _Script([])], _registry(_Clock()), log)
    assert (await model.ainvoke(PROMPT)).content == "ok"
    assert _waits == [2.0]
    assert log.models == ["m0", "m0"]


# Scenario: An empty answer is re-rolled before moving on
async def test_empty_answer_is_rerolled_then_moves_on() -> None:
    log, clock = CallLog(), _Clock()
    registry = _registry(clock)
    model = _queue([_Script([], reply=""), _Script([], reply="filled")], registry, log)
    assert (await model.ainvoke(PROMPT)).content == "filled"
    assert log.models.count("m0") == 3
    assert registry.get("m0").state is BreakerState.CLOSED


# Scenario: Only one probe passes a half-open breaker
def test_only_one_probe_passes() -> None:
    clock = _Clock()
    breaker = _registry(clock).get("m0")
    breaker.record_failure(FailureClass.QUOTA)
    clock.now += BreakerPolicy().quota_cooldown + 1
    assert breaker.try_acquire() is True
    assert breaker.state is BreakerState.HALF_OPEN
    assert breaker.try_acquire() is False


# Scenario: A failed probe doubles the cooldown
def test_failed_probe_doubles_the_cooldown() -> None:
    clock, policy = _Clock(), BreakerPolicy()
    breaker = _registry(clock).get("m0")
    for _ in range(policy.failure_threshold):
        breaker.record_failure(FailureClass.TRANSIENT)
    assert breaker.cooldown == policy.cooldown
    clock.now += policy.cooldown + 1
    assert breaker.try_acquire() is True
    breaker.record_failure(FailureClass.TRANSIENT)
    assert breaker.cooldown == policy.cooldown * 2
    breaker.cooldown = policy.max_cooldown
    clock.now += policy.max_cooldown + 1
    breaker.try_acquire()
    breaker.record_failure(FailureClass.TRANSIENT)
    assert breaker.cooldown == policy.max_cooldown


def test_success_closes_and_resets() -> None:
    clock = _Clock()
    breaker = _registry(clock).get("m0")
    breaker.record_failure(FailureClass.FATAL)
    clock.now += BreakerPolicy().fatal_cooldown + 1
    breaker.try_acquire()
    breaker.record_success()
    assert breaker.state is BreakerState.CLOSED
    assert breaker.describe() == "closed"


# Scenario: All models down fails fast with every state named
async def test_all_models_down_names_every_state() -> None:
    log, down = CallLog(), []
    model = _queue(
        [
            _Script([StatusError(403, "FreeTierError")] * 3),
            _Script([StatusError(429, "GoUsageLimitError")] * 3),
        ],
        _registry(_Clock()),
        log,
        down,
    )
    with pytest.raises(AllModelsUnavailableError) as raised:
        await model.ainvoke(PROMPT)
    assert "m0=open" in str(raised.value) and "m1=open" in str(raised.value)
    assert len(down) == 1


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (StatusError(401), FailureClass.FATAL),
        (OpenCodeSidecarError("FreeTierError: free tier", 403), FailureClass.FATAL),
        (StatusError(429, "GoUsageLimitError"), FailureClass.QUOTA),
        (StatusError(429, "slow down"), FailureClass.THROTTLED),
        (StatusError(502), FailureClass.TRANSIENT),
        (TimeoutError(), FailureClass.TRANSIENT),
    ],
)
def test_classify_failure(error: Exception, expected: FailureClass) -> None:
    assert classify_failure(error) is expected


# Scenario: The OpenCode sidecar is called with Basic auth and one session per call
async def test_sidecar_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "POST" and request.url.path == "/session":
            return httpx.Response(200, json={"id": "ses_1"})
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"info": {}, "parts": [{"type": "text", "text": '{"ok": true}'}]},
            )
        return httpx.Response(200, json=True)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        sidecar_module.httpx,
        "AsyncClient",
        functools.partial(httpx.AsyncClient, transport=transport),
    )
    model = OpenCodeSidecarChatModel(
        model_name="opencode/deepseek-v4.1-flash-free",
        base_url="http://opencode:4096",
        password=SecretStr("pw"),
    )
    from langchain_core.messages import HumanMessage, SystemMessage

    result = await model.ainvoke([
        SystemMessage(content="Seja breve."),
        HumanMessage(content=PROMPT),
    ])

    assert result.content == '{"ok": true}'
    assert [r.method for r in seen] == ["POST", "POST", "DELETE"]
    body = json.loads(seen[1].content)
    assert body["model"] == {
        "providerID": "opencode",
        "modelID": "deepseek-v4.1-flash-free",
    }
    assert body["system"] == "Seja breve."
    assert seen[1].headers["authorization"].startswith("Basic ")


# Scenario: A sidecar model error keeps the provider status for the breaker
async def test_sidecar_model_error_is_classified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = {
        "name": "APIError",
        "data": {
            "message": "free tier only in OpenCode",
            "statusCode": 403,
            "responseBody": "FreeTierError",
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/session" and request.method == "POST":
            return httpx.Response(200, json={"id": "ses_2"})
        if request.method == "POST":
            return httpx.Response(200, json={"info": {"error": error}, "parts": []})
        return httpx.Response(200, json=True)

    monkeypatch.setattr(
        sidecar_module.httpx,
        "AsyncClient",
        functools.partial(httpx.AsyncClient, transport=httpx.MockTransport(handler)),
    )
    model = OpenCodeSidecarChatModel(
        model_name="opencode/x", base_url="http://opencode:4096"
    )
    with pytest.raises(OpenCodeSidecarError) as raised:
        await model.ainvoke(PROMPT)
    assert raised.value.status_code == 403
    assert classify_failure(raised.value) is FailureClass.FATAL


# Scenario: Breaker changes are alerted once and all-down is rate-limited
async def test_alerts_dedupe_and_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []

    async def _post(self: TelegramLlmAlerts, text: str) -> None:
        sent.append(text)

    monkeypatch.setattr(TelegramLlmAlerts, "_post", _post)
    clock = _Clock()
    alerts = TelegramLlmAlerts(token="t", chat_id="c", clock=clock)
    alerts.on_transition(
        BreakerTransition(
            "m0",
            BreakerState.CLOSED,
            BreakerState.OPEN,
            FailureClass.QUOTA,
            3600.0,
            "weekly",
        )
    )
    alerts.on_transition(
        BreakerTransition("m0", BreakerState.OPEN, BreakerState.HALF_OPEN)
    )
    alerts.on_all_down("fast", "m0=open")
    clock.now += 60
    alerts.on_all_down("fast", "m0=open")
    import asyncio

    await asyncio.sleep(0)
    assert len(sent) == 2
    assert "m0" in sent[0] and "60 min" in sent[0]
    assert "All LLM models unavailable" in sent[1]


def test_alerts_without_token_are_a_noop() -> None:
    alerts = TelegramLlmAlerts(token="", chat_id="")
    assert alerts.enabled is False
    alerts.on_all_down("fast", "x")


def _settings(**overrides: str) -> Settings:
    base: dict[str, str | SecretStr] = {
        "secret_key": "test-secret-key-for-ci-tests!!",
        "anon_secret_key": "test-anon-secret-for-ci-tests!",
        "llm_provider": "glm",
        "glm_api_key": SecretStr("glm-key"),
    }
    return Settings.model_validate({**base, **overrides})


def test_queue_spec_parsing() -> None:
    settings = _settings(
        llm_model_queue_fast="sidecar:opencode/deepseek-v4.1-flash-free, go:deepseek-v4.1-flash,qwen3.8-flash"
    )
    assert queue_spec(settings, LLM_ROLE_FAST) == [
        ("sidecar", "opencode/deepseek-v4.1-flash-free"),
        ("go", "deepseek-v4.1-flash"),
        ("go", "qwen3.8-flash"),
    ]


def test_queue_is_built_when_configured() -> None:
    settings = _settings(
        llm_model_queue_fast="sidecar:opencode/deepseek-v4.1-flash-free,go:deepseek-v4.1-flash,go:qwen3.8-flash",
        opencode_sidecar_url="http://opencode:4096",
    )
    model = build_chat_model(settings, LLM_ROLE_FAST)
    assert isinstance(model, ModelQueueChatModel)
    assert [getattr(m, "model_name", "") for m in model.models] == [
        "opencode/deepseek-v4.1-flash-free",
        "deepseek-v4.1-flash",
        "qwen3.8-flash",
    ]


def test_sidecar_entry_is_dropped_without_a_url() -> None:
    settings = _settings(
        llm_model_queue_fast="sidecar:opencode/x,go:deepseek-v4.1-flash"
    )
    model = build_chat_model(settings, LLM_ROLE_FAST)
    assert isinstance(model, ModelQueueChatModel)
    assert len(model.models) == 1


# Scenario: Without a queue setting the AE-0391 routing is kept
def test_no_queue_keeps_the_routed_model() -> None:
    assert isinstance(build_chat_model(_settings(), LLM_ROLE_FAST), RoutedChatModel)


# Scenario: JSON that never parses moves on to the rest of the queue
async def test_bad_json_moves_on_to_the_rest_of_the_queue() -> None:
    log = CallLog()
    model = _queue(
        [_Script([], reply="not json"), _Script([], reply='{"ok": 1}')],
        _registry(_Clock()),
        log,
    )
    policy = JsonRetryPolicy(parse=json.loads, agent="test", model_id="m0")
    parsed, _raw = await ainvoke_json(model, PROMPT, policy)
    assert parsed == {"ok": 1}
    assert "m1" in log.models
    assert model.as_fallback() is not None
    last = model.as_fallback()
    assert last is not None and last.as_fallback() is None
