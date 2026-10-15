"""AE-0391: bad JSON after the existing retry falls back to the GLM model.

Scenarios: see tests/features/llm_model_routing_ae0391.feature
"""

from __future__ import annotations

import json

import pytest
from structlog.testing import capture_logs

from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.infrastructure.config.llm_routing_constants import (
    LLM_ROLE_FAST,
    LLM_TAG_FALLBACK,
    LOG_LLM_JSON_FALLBACK_USED,
)
from rag_backend.infrastructure.external.routed_chat_model import RoutedChatModel
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat


def _parse(raw: str) -> dict[str, object]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(ERR_INVALID_JSON) from exc
    if not isinstance(data, dict):
        raise TypeError(ERR_INVALID_JSON)
    return data


POLICY = JsonRetryPolicy(parse=_parse, agent="content_draft", model_id="content-draft")


def _routed(log: CallLog, fallback_reply: str | None) -> RoutedChatModel:
    fallback = (
        None
        if fallback_reply is None
        else FakeChat(model_name="glm", log=log, reply=lambda _p: fallback_reply)
    )
    return RoutedChatModel(
        primary=FakeChat(model_name="deepseek", log=log, reply=lambda _p: "not json"),
        fallback=fallback,
        role=LLM_ROLE_FAST,
        timeout_seconds=5.0,
    )


async def test_bad_json_after_retry_is_reissued_on_the_fallback() -> None:
    # Scenario: bad JSON after the existing retry falls back
    log = CallLog()
    model = _routed(log, '{"draft_text": "ok"}')

    with capture_logs() as logs:
        parsed, raw = await ainvoke_json(model.bind(temperature=0.3), "p", POLICY)

    assert parsed == {"draft_text": "ok"}
    assert raw == '{"draft_text": "ok"}'
    # first attempt + repair on the primary, then the fallback answers.
    assert log.models == ["deepseek", "deepseek", "glm"]
    assert LLM_TAG_FALLBACK in log.tags[2]
    assert log.kwargs[2].get("temperature") == 0.3
    events = [e for e in logs if e["event"] == LOG_LLM_JSON_FALLBACK_USED]
    assert len(events) == 1
    assert events[0]["reason"] == "bad_json"


async def test_non_dict_json_also_falls_back() -> None:
    log = CallLog()
    model = _routed(log, '{"a": 1}')
    model.primary = FakeChat(model_name="deepseek", log=log, reply=lambda _p: "[1]")

    parsed, _raw = await ainvoke_json(model, "p", POLICY)

    assert parsed == {"a": 1}


async def test_without_fallback_the_error_contract_is_unchanged() -> None:
    # Scenario: no fallback configured keeps the existing error contract
    model = _routed(CallLog(), None)

    with pytest.raises(ValueError, match=ERR_INVALID_JSON):
        await ainvoke_json(model, "p", POLICY)


async def test_fallback_that_also_fails_raises_invalid_json() -> None:
    log = CallLog()
    model = _routed(log, "still not json")

    with pytest.raises(ValueError, match=ERR_INVALID_JSON):
        await ainvoke_json(model, "p", POLICY)

    assert log.models == ["deepseek", "deepseek", "glm", "glm"]
