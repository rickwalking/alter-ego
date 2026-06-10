"""Content draft agent with persona enforcement (AI-008)."""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.instruction_context_loader import (
    CarouselInstructionContextLoader,
    InstructionContextRequest,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
    render_presentation_policy_context,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel import CAROUSEL_PROMPT_VERSION_V3
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
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
        self._instruction_loader = CarouselInstructionContextLoader()

    async def draft_slide(
        self,
        slide_index: int,
        title: str,
        key_points: list[str],
        persona: PersonaProfile | None = None,
        persona_context: str = "",
        *,
        locale: str = "pt",
        revision_notes: str = "",
    ) -> dict[str, object]:
        """Draft copy for a single slide."""
        title = sanitize_llm_input(title)
        safe_points = [sanitize_llm_input(p) for p in key_points]
        persona_context = sanitize_llm_input(persona_context)
        revision_notes = sanitize_llm_input(revision_notes)

        instruction = self._instruction_loader.load(
            InstructionContextRequest(
                phase=PHASE_CONTENT,
                locale=locale,
                persona_context=persona_context,
                revision_notes=revision_notes,
                slide_number=slide_index,
                prompt_version=CAROUSEL_PROMPT_VERSION_V3,
            )
        )
        policy = load_presentation_policy(instruction.policy_version)
        prompt_text, _ = render_prompt(
            "carousel",
            "content",
            variables={
                "slide_number": slide_index,
                "title": title,
                "key_points": ", ".join(safe_points),
                "locale": locale,
                "phase": PHASE_CONTENT,
                "presentation_policy_context": render_presentation_policy_context(policy),
                "persona_context": persona_context or "Default professional voice.",
                "revision_notes": revision_notes or "None.",
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

        draft = self._parse_draft(raw)
        draft["instruction_checksum"] = instruction.checksum
        draft["policy_version"] = instruction.policy_version
        draft["prompt_version"] = instruction.prompt_version
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
            draft: dict[str, object] = {
                "draft_text": str(data.get("draft_text", "")),
                "confidence_score": float(data.get("confidence_score", 0.5)),
                "sources_used": list(data.get("sources_used", [])),
            }
        except (TypeError, ValueError) as exc:
            raise ValueError(ERR_INVALID_JSON) from exc
        icon_name = data.get("icon_name")
        if isinstance(icon_name, str) and icon_name.strip():
            draft["icon_name"] = icon_name.strip()
        long_form_notes = data.get("long_form_notes")
        if isinstance(long_form_notes, str) and long_form_notes.strip():
            draft["long_form_notes"] = long_form_notes.strip()
        return draft


__all__ = ["ContentDraftAgent"]
