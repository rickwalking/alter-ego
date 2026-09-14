"""Shared JSON-response retry policy for carousel agents (AE-0330).

Live 2026-09-14: GLM 5.2 returned empty content on the outline phase (its
reasoning consumed 31999 of 32000 tokens) and again on the content phase. Both
agents failed the whole workflow on that single bad response, while
``source_synthesis_agent`` — hardened by AE-0318 — survived the same class of
failure because it retries. This module carries that tolerance to every caller.

Two distinct failures need two different remedies:

* **Empty content** is a sampling tail event, so there is nothing to repair —
  re-roll the original call. Evidence: the outline prompt that burned 31999
  reasoning tokens used 7548 on the very next attempt and parsed cleanly.
* **Malformed but present** output can be fixed by the model itself, so hand it
  back with ``JSON_REPAIR_PROMPT`` (the AE-0318 round-trip).

Each remedy costs at most one extra call, and only on the failure path.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import Runnable

from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.infrastructure.llm.json_utils import JSON_REPAIR_PROMPT
from rag_backend.infrastructure.logging import get_logger
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config

T = TypeVar("T")

logger = get_logger()

_LOG_PREVIEW_CHARS = 500


@dataclass(frozen=True)
class JsonRetryPolicy(Generic[T]):
    """How to parse a response and how to describe it in logs."""

    parse: Callable[[str], T]
    agent: str
    model_id: str


async def ainvoke_json(
    runnable: Runnable[LanguageModelInput, BaseMessage],
    prompt: str,
    policy: JsonRetryPolicy[T],
) -> tuple[T, str]:
    """Return the parsed response and the raw text that produced it.

    Raises ``ValueError(ERR_INVALID_JSON)`` only after both the re-roll and the
    repair round-trip have been exhausted, so callers keep their existing
    error contract.
    """
    raw = await _ainvoke_once(runnable, prompt)
    if not raw.strip():
        logger.warning(
            "llm_empty_response_rerolling",
            agent=policy.agent,
            model_id=policy.model_id,
        )
        raw = await _ainvoke_once(runnable, prompt)
        if not raw.strip():
            logger.warning(
                "llm_empty_response_after_reroll",
                agent=policy.agent,
                model_id=policy.model_id,
            )
            raise ValueError(ERR_INVALID_JSON)
    try:
        return policy.parse(raw), raw
    except (ValueError, TypeError):
        logger.warning(
            "llm_json_parse_failed_attempt_1",
            agent=policy.agent,
            model_id=policy.model_id,
            raw_response=raw[:_LOG_PREVIEW_CHARS],
        )
    repaired = await _arequest_repair(runnable, raw, policy)
    try:
        return policy.parse(repaired), repaired
    except (ValueError, TypeError):
        logger.exception(
            "llm_json_parse_failed_attempt_2",
            agent=policy.agent,
            model_id=policy.model_id,
            repair_response=repaired[:_LOG_PREVIEW_CHARS],
        )
        raise


async def _ainvoke_once(
    runnable: Runnable[LanguageModelInput, BaseMessage],
    prompt: str,
) -> str:
    messages: list[BaseMessage] = [HumanMessage(content=prompt)]
    response = await runnable.ainvoke(messages, get_langfuse_runnable_config())
    return cast(str, response.content)


async def _arequest_repair(
    runnable: Runnable[LanguageModelInput, BaseMessage],
    raw: str,
    policy: JsonRetryPolicy[T],
) -> str:
    """Ask the model to correct its own malformed JSON.

    A transport failure during the repair is folded into the same
    ``ValueError`` contract as a failed parse, so no new 500 path appears.
    """
    messages: list[BaseMessage] = [
        AIMessage(content=raw),
        HumanMessage(content=JSON_REPAIR_PROMPT),
    ]
    try:
        response = await runnable.ainvoke(messages, get_langfuse_runnable_config())
    except Exception as exc:
        logger.warning(
            "llm_json_repair_call_failed",
            agent=policy.agent,
            model_id=policy.model_id,
            error=str(exc),
        )
        raise ValueError(ERR_INVALID_JSON) from exc
    return cast(str, response.content)


__all__ = ["JsonRetryPolicy", "ainvoke_json"]
