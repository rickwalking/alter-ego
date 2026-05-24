"""Outline generation agent with human-editable output (AI-007)."""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON, PROMPT_OUTLINE_GENERATION
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_handler


class OutlineAgent:
    """Generates human-editable carousel outlines."""

    def __init__(self, llm: BaseChatModel, model_id: str = "outline-agent") -> None:
        self.llm = llm
        self.model_id = model_id
        self._cache = get_ai_response_cache()

    async def generate_outline(
        self,
        topic: str,
        audience: str,
        brief: str,
        sources: list[str],
    ) -> list[dict[str, object]]:
        """Generate a slide-by-slide outline."""
        topic = sanitize_llm_input(topic)
        audience = sanitize_llm_input(audience)
        brief = sanitize_llm_input(brief)
        safe_sources = "\n".join(sanitize_llm_input(s) for s in sources)

        prompt = PROMPT_OUTLINE_GENERATION.format(
            topic=topic,
            audience=audience,
            brief=brief,
            sources=safe_sources or "None",
        )
        cached = self._cache.get(prompt, self.model_id)
        raw = cached
        if raw is None:
            messages: list[BaseMessage] = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages, callbacks=get_langfuse_handler())
            raw = cast(str, response.content)
            self._cache.set(prompt, self.model_id, raw)

        return self._parse_outline(raw)

    def _parse_outline(self, raw: str) -> list[dict[str, object]]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(ERR_INVALID_JSON) from exc
        if not isinstance(data, list):
            raise TypeError(ERR_INVALID_JSON)
        outline: list[dict[str, object]] = []
        for item in data:
            if isinstance(item, dict):
                outline.append(item)
        return outline


__all__ = ["OutlineAgent"]
