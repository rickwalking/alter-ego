"""Source synthesis agent — extracts key points from uploaded materials (AI-006)."""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.constants.ai_agents import (
    ERR_INVALID_JSON,
    PROMPT_SOURCE_SYNTHESIS,
)
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.llm.json_utils import extract_json
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config


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
        cached = self._cache.get(prompt, self.model_id)
        if cached is not None:
            return self._parse_response(cached)

        messages: list[BaseMessage] = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages, get_langfuse_runnable_config())
        raw = cast(str, response.content)
        self._cache.set(prompt, self.model_id, raw)
        return self._parse_response(raw)

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
