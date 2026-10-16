"""Same-model retries before the fallback, and non-GLM fallbacks (AE-0395).

Gherkin: tests/features/llm_retry_ae0395.feature
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from pydantic import SecretStr
from structlog.testing import capture_logs

from rag_backend.agents import llm_json_retry
from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
from rag_backend.infrastructure.config.llm_routing_constants import (
    LLM_ATTEMPTS_PER_MODEL,
    LLM_ROLE_FAST,
    LLM_ROLE_REASONING,
    LOG_LLM_JSON_RETRY,
    LOG_LLM_RETRY,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external import routed_chat_model
from rag_backend.infrastructure.external.chat_model_factory import build_chat_model
from rag_backend.infrastructure.external.routed_chat_model import (
    RoutedChatModel,
    model_id_of,
    retry_delay,
)
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat

pytestmark = pytest.mark.unit

PROMPT = "Escreva a legenda."


class StatusError(RuntimeError):
    def __init__(self, status: int) -> None:
        super().__init__(f"status {status}")
        self.status_code = status


@dataclass
class _Flaky:
    """Fails the first ``failures`` calls, then answers ``reply``."""

    failures: int
    reply: str = "ok"
    calls: list[int] = field(default_factory=list)

    def __call__(self, _prompt: str) -> str:
        self.calls.append(1)
        if len(self.calls) <= self.failures:
            raise StatusError(503)
        return self.reply


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waits: list[float] = []

    async def _record(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(routed_chat_model, "_sleep", _record)
    return waits


def _model(
    primary: Callable[[str], str], fallback: Callable[[str], str], log: CallLog
) -> RoutedChatModel:
    return RoutedChatModel(
        primary=FakeChat(model_name="flash", log=log, reply=primary),
        fallback=FakeChat(model_name="qwen", log=log, reply=fallback),
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
    )


def _always_fail(_prompt: str) -> str:
    raise StatusError(503)


# Scenario: A transient failure is retried on the same model
async def test_transient_failure_is_retried_on_the_same_model() -> None:
    log = CallLog()
    model = _model(_Flaky(failures=2, reply="third time"), _always_fail, log)

    with capture_logs() as logs:
        result = await model.ainvoke(PROMPT)

    assert result.content == "third time"
    assert log.models == ["flash", "flash", "flash"]
    retries = [e for e in logs if e["event"] == LOG_LLM_RETRY]
    assert [e["attempt"] for e in retries] == [1, 2]


# Scenario: The fallback is used only after 5 failed attempts
async def test_fallback_only_after_five_attempts() -> None:
    log = CallLog()
    model = _model(_always_fail, lambda _p: "from qwen", log)

    result = await model.ainvoke(PROMPT)

    assert result.content == "from qwen"
    assert log.models == ["flash"] * LLM_ATTEMPTS_PER_MODEL + ["qwen"]


# Scenario: The fallback also gets 5 attempts
async def test_fallback_also_gets_five_attempts() -> None:
    log = CallLog()
    model = _model(_always_fail, _always_fail, log)

    with pytest.raises(StatusError):
        await model.ainvoke(PROMPT)

    assert log.models == ["flash"] * 5 + ["qwen"] * 5


# Scenario: Auth errors are not retried
@pytest.mark.parametrize("status", [401, 403])
async def test_auth_error_is_not_retried(status: int) -> None:
    log = CallLog()
    model = RoutedChatModel(
        primary=FakeChat(model_name="flash", log=log, error=StatusError(status)),
        fallback=FakeChat(model_name="qwen", log=log),
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
    )

    with pytest.raises(StatusError):
        await model.ainvoke(PROMPT)

    assert log.models == ["flash"]


# Scenario: Backoff grows and is capped
def test_backoff_grows_and_is_capped() -> None:
    assert [retry_delay(n) for n in range(1, 6)] == [2.0, 4.0, 8.0, 15.0, 15.0]


async def test_waits_between_attempts_use_the_backoff(_no_backoff: list[float]) -> None:
    model = _model(_Flaky(failures=3), _always_fail, CallLog())

    await model.ainvoke(PROMPT)

    assert _no_backoff == [2.0, 4.0, 8.0]


# Scenario: Bad JSON is retried on the same model before the fallback
async def test_bad_json_gets_five_attempts_before_the_fallback() -> None:
    log = CallLog()
    model = _model(
        lambda _p: "uma legenda em prosa", lambda _p: '{"caption": "ok"}', log
    )
    policy = JsonRetryPolicy(
        parse=_parse_caption, agent="distribution", model_id="flash"
    )

    with capture_logs() as logs:
        parsed, _raw = await ainvoke_json(model, PROMPT, policy)

    assert parsed == {"caption": "ok"}
    assert log.models.count("flash") >= llm_json_retry.LLM_ATTEMPTS_PER_MODEL
    assert log.models[-1] == "qwen"
    retries = [e["attempt"] for e in logs if e["event"] == LOG_LLM_JSON_RETRY]
    assert retries == [1, 2, 3, 4]


def _parse_caption(raw: str) -> dict[str, object]:
    import json

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("not an object")
    return data


# Scenario: Each role falls back to a fast non-GLM model
@pytest.mark.parametrize(
    ("role", "fallback"),
    [(LLM_ROLE_FAST, "qwen3.8-flash"), (LLM_ROLE_REASONING, "qwen3.8-max")],
)
def test_each_role_falls_back_to_a_non_glm_model(role: str, fallback: str) -> None:
    settings = Settings(llm_provider="glm", glm_api_key=SecretStr("glm-key"))

    model = build_chat_model(settings, role)

    assert isinstance(model, RoutedChatModel)
    assert model.fallback is not None
    assert model_id_of(model.fallback) == fallback
    assert "glm" not in model_id_of(model.fallback)
