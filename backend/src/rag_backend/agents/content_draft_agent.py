"""Content draft agent with persona enforcement (AI-008)."""

from __future__ import annotations

import json

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
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
from rag_backend.domain.constants.carousel import CAROUSEL_PROMPT_VERSION_V4
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.llm.json_utils import extract_json
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_MODEL_CFG_TEMPERATURE = "temperature"
_MODEL_CFG_MAX_TOKENS = "max_tokens"
_BINDABLE_MODEL_KEYS = (_MODEL_CFG_TEMPERATURE, _MODEL_CFG_MAX_TOKENS)


def _model_bind_kwargs(model_cfg: dict[str, object]) -> dict[str, object]:
    """Extract numeric temperature/max_tokens overrides from the prompt YAML."""
    bind_kwargs: dict[str, object] = {}
    for key in _BINDABLE_MODEL_KEYS:
        value = model_cfg.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            bind_kwargs[key] = value
    return bind_kwargs


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
        sibling_context: str = "",
        previous_draft: str = "",
    ) -> dict[str, object]:
        """Draft copy for a single slide."""
        title = sanitize_llm_input(title)
        safe_points = [sanitize_llm_input(p) for p in key_points]
        persona_context = sanitize_llm_input(persona_context)
        revision_notes = sanitize_llm_input(revision_notes)
        sibling_context = sanitize_llm_input(sibling_context)
        previous_draft = sanitize_llm_input(previous_draft)

        instruction = self._instruction_loader.load(
            InstructionContextRequest(
                phase=PHASE_CONTENT,
                locale=locale,
                persona_context=persona_context,
                revision_notes=revision_notes,
                slide_number=slide_index,
                prompt_version=CAROUSEL_PROMPT_VERSION_V4,
                sibling_context=sibling_context,
                previous_draft=previous_draft,
            )
        )
        policy = load_presentation_policy(instruction.policy_version)
        # AE-0291: revision notes are rendered ONCE, in the instruction context above.
        # The v4 template no longer carries a second {{ revision_notes }} block.
        prompt_text, model_cfg = render_prompt(
            "carousel",
            "content",
            variables={
                "slide_number": slide_index,
                "title": title,
                "key_points": ", ".join(safe_points),
                "locale": locale,
                "phase": PHASE_CONTENT,
                "presentation_policy_context": render_presentation_policy_context(
                    policy
                ),
                "persona_context": persona_context or "Default professional voice.",
            },
            version=CAROUSEL_PROMPT_VERSION_V4,
        )
        full_prompt = f"{instruction.instruction}\n\n{prompt_text}"
        cached = self._cached_raw(full_prompt)
        if cached is not None:
            draft = self._parse_draft(cached)
        else:
            # AE-0291: apply the v4 YAML model config (temperature/max_tokens) via a
            # per-call .bind — previously discarded, so the knobs were inert.
            runnable = self._runnable_with_model_config(model_cfg)
            # AE-0330: one bad response used to fail the whole workflow — GLM 5.2
            # returned empty content live on 2026-09-14 and the phase died.
            # Re-roll an empty response, repair a malformed one, and cache only
            # what parsed (an unparseable raw poisons every retry for the TTL).
            draft, raw = await ainvoke_json(
                runnable,
                full_prompt,
                JsonRetryPolicy(
                    parse=self._parse_draft,
                    agent="content_draft",
                    model_id=self.model_id,
                ),
            )
            self._cache.set(full_prompt, self.model_id, raw)
        draft["instruction_checksum"] = instruction.checksum
        draft["policy_version"] = instruction.policy_version
        draft["prompt_version"] = instruction.prompt_version
        if persona is not None:
            persona_agent = PersonaAgent(persona=persona, llm=self.llm)
            enforced = await persona_agent.enforce(str(draft.get("draft_text", "")))
            draft["draft_text"] = enforced
        return draft

    def _cached_raw(self, prompt: str) -> str | None:
        """Return a cached response only while it still parses, evicting poison.

        An entry written by an older deploy (or any response that stopped being
        parseable) is dropped so the caller falls through to a fresh LLM call
        instead of replaying the failure until the TTL expires.
        """
        cached = self._cache.get(prompt, self.model_id)
        if cached is None:
            return None
        try:
            self._parse_draft(cached)
        except (ValueError, TypeError):
            self._cache.delete(prompt, self.model_id)
            logger.warning(
                "content_draft_poisoned_cache_evicted",
                model_id=self.model_id,
            )
            return None
        return cached

    def _runnable_with_model_config(
        self, model_cfg: dict[str, object]
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """AE-0291: bind supported sampling knobs from the prompt YAML model block."""
        bind_kwargs = _model_bind_kwargs(model_cfg)
        if not bind_kwargs:
            return self.llm
        return self.llm.bind(**bind_kwargs)

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
