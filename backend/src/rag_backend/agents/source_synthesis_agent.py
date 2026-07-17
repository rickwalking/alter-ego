"""Source synthesis agent — extracts key points from uploaded materials (AI-006)."""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.constants.ai_agents import (
    ERR_INVALID_JSON,
    PROMPT_SOURCE_SYNTHESIS,
)
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.llm.json_utils import JSON_REPAIR_PROMPT, extract_json
from rag_backend.infrastructure.logging import get_logger
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config

logger = get_logger()


class SourceSynthesisAgent:
    """Synthesizes curated sources into key points for editorial workflows."""

    def __init__(self, llm: BaseChatModel, model_id: str = "source-synthesis") -> None:
        self.llm = llm
        self.model_id = model_id
        self._cache = get_ai_response_cache()

    async def extract_key_points(
        self,
        title: str,
        content: str,
        source_type: str = "document",
    ) -> dict[str, object]:
        """Extract key points and summary from source content."""
        title = sanitize_llm_input(title)
        content = sanitize_llm_input(content)
        source_type = sanitize_llm_input(source_type)

        prompt = PROMPT_SOURCE_SYNTHESIS.format(
            title=title,
            source_type=source_type,
            content=content,
        )
        cached = self._parse_cached(prompt)
        if cached is not None:
            return cached

        messages: list[BaseMessage] = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages, get_langfuse_runnable_config())
        raw = cast(str, response.content)
        parsed, good_raw = await self._parse_with_repair(raw)
        # AE-0318: cache only a response that parsed — a truncated/malformed raw
        # cached here poisons every retry for the TTL window.
        self._cache.set(prompt, self.model_id, good_raw)
        return parsed

    def _parse_cached(self, prompt: str) -> dict[str, object] | None:
        """Return parsed findings from cache, evicting entries that fail to parse."""
        cached = self._cache.get(prompt, self.model_id)
        if cached is None:
            return None
        try:
            return self._parse_response(cached)
        except (ValueError, TypeError):
            # Poisoned entry (e.g. written by a pre-AE-0318 deploy): evict and
            # fall through to a fresh LLM call instead of replaying the failure.
            self._cache.delete(prompt, self.model_id)
            logger.warning(
                "source_synthesis_poisoned_cache_evicted",
                model_id=self.model_id,
            )
            return None

    async def _parse_with_repair(self, raw: str) -> tuple[dict[str, object], str]:
        """Parse the response, allowing one LLM repair round-trip on failure."""
        try:
            return self._parse_response(raw), raw
        except (ValueError, TypeError):
            logger.warning(
                "source_synthesis_json_parse_failed_attempt_1",
                model_id=self.model_id,
                raw_response=raw[:500],
            )
        repaired = await self._request_repair(raw)
        try:
            return self._parse_response(repaired), repaired
        except (ValueError, TypeError):
            logger.exception(
                "source_synthesis_json_parse_failed_attempt_2",
                model_id=self.model_id,
                repair_response=repaired[:500],
            )
            raise

    async def _request_repair(self, raw: str) -> str:
        """Ask the model to correct its own malformed JSON response."""
        messages: list[BaseMessage] = [
            AIMessage(content=raw),
            HumanMessage(content=JSON_REPAIR_PROMPT),
        ]
        response = await self.llm.ainvoke(messages, get_langfuse_runnable_config())
        return cast(str, response.content)

    def _parse_response(self, raw: str) -> dict[str, object]:
        try:
            data = extract_json(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(ERR_INVALID_JSON) from exc
        if not isinstance(data, dict):
            raise TypeError(ERR_INVALID_JSON)
        key_points = data.get("key_points", [])
        if not isinstance(key_points, list):
            key_points = []
        return {
            "key_points": [str(point) for point in key_points],
            "summary": str(data.get("summary", "")),
        }


__all__ = ["SourceSynthesisAgent"]
