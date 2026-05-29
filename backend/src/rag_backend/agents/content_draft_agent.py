"""Content draft agent with persona enforcement (AI-008)."""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.domain.constants.ai_agents import (
    ERR_INVALID_JSON,
    PROMPT_CONTENT_DRAFT,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.llm.json_utils import extract_json
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config


class ContentDraftAgent:
    """Drafts carousel slide copy with optional persona enforcement."""

    def __init__(self, llm: BaseChatModel, model_id: str = "content-draft") -> None:
        self.llm = llm
        self.model_id = model_id
        self._cache = get_ai_response_cache()

    async def draft_slide(
        self,
        slide_index: int,
        title: str,
        key_points: list[str],
        persona: PersonaProfile | None = None,
        persona_context: str = "",
    ) -> dict[str, object]:
        """Draft copy for a single slide."""
        title = sanitize_llm_input(title)
        safe_points = [sanitize_llm_input(p) for p in key_points]
        persona_context = sanitize_llm_input(persona_context)

        prompt = PROMPT_CONTENT_DRAFT.format(
            slide_index=slide_index,
            title=title,
            key_points=", ".join(safe_points),
            persona_context=persona_context or "Default professional voice",
        )
        cached = self._cache.get(prompt, self.model_id)
        raw = cached
        if raw is None:
            messages: list[BaseMessage] = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages, get_langfuse_runnable_config())
            raw = cast(str, response.content)
            self._cache.set(prompt, self.model_id, raw)

        draft = self._parse_draft(raw)
        if persona is not None:
            persona_agent = PersonaAgent(persona=persona, llm=self.llm)
            enforced = await persona_agent.enforce(str(draft.get("draft_text", "")))
            draft["draft_text"] = enforced
        return draft

    def _parse_draft(self, raw: str) -> dict[str, object]:
        try:
            data = extract_json(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(ERR_INVALID_JSON) from exc
        if not isinstance(data, dict):
            raise TypeError(ERR_INVALID_JSON)
        try:
            return {
                "draft_text": str(data.get("draft_text", "")),
                "confidence_score": float(data.get("confidence_score", 0.5)),
                "sources_used": list(data.get("sources_used", [])),
            }
        except (TypeError, ValueError) as exc:
            raise ValueError(ERR_INVALID_JSON) from exc


__all__ = ["ContentDraftAgent"]
