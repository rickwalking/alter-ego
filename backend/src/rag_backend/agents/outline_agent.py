"""Outline generation agent with human-editable output (AI-007)."""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.instruction_context_loader import (
    CarouselInstructionContextLoader,
    InstructionContextRequest,
)
from rag_backend.application.services.carousel.outline_normalize import (
    normalize_editorial_outline,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
    render_presentation_policy_context,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel import CAROUSEL_PROMPT_VERSION_V3
from rag_backend.domain.constants.carousel_workflow import PHASE_OUTLINE
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.llm.json_utils import extract_json
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config


class OutlineAgent:
    """Generates human-editable carousel outlines."""

    def __init__(self, llm: BaseChatModel, model_id: str = "outline-agent") -> None:
        self.llm = llm
        self.model_id = model_id
        self._cache = get_ai_response_cache()
        self._instruction_loader = CarouselInstructionContextLoader()

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

        instruction = self._instruction_loader.load(
            InstructionContextRequest(
                phase=PHASE_OUTLINE,
                locale="pt",
                prompt_version=CAROUSEL_PROMPT_VERSION_V3,
            )
        )
        policy = load_presentation_policy(instruction.policy_version)
        prompt_text, _ = render_prompt(
            "carousel",
            "outline",
            variables={
                "topic": topic,
                "audience": audience,
                "brief": brief,
                "sources": safe_sources or "None",
                "locale": "pt",
                "phase": PHASE_OUTLINE,
                "slide_count": policy.slide_count,
                "presentation_policy_context": render_presentation_policy_context(policy),
                "persona_context": "",
                "revision_notes": "",
            },
            version=CAROUSEL_PROMPT_VERSION_V3,
        )
        full_prompt = f"{instruction.instruction}\n\n{prompt_text}"
        cached = self._cache.get(full_prompt, self.model_id)
        raw = cached
        if raw is None:
            messages: list[BaseMessage] = [HumanMessage(content=full_prompt)]
            response = await self.llm.ainvoke(messages, get_langfuse_runnable_config())
            raw = cast(str, response.content)
            self._cache.set(full_prompt, self.model_id, raw)

        return self._parse_outline(raw)

    def _parse_outline(self, raw: str) -> list[dict[str, object]]:
        try:
            data = extract_json(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(ERR_INVALID_JSON) from exc
        if not isinstance(data, list):
            raise TypeError(ERR_INVALID_JSON)
        outline: list[dict[str, object]] = [
            item for item in data if isinstance(item, dict)
        ]
        return normalize_editorial_outline(outline)


__all__ = ["OutlineAgent"]
