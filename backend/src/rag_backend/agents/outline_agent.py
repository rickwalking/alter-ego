"""Outline generation agent with human-editable output (AI-007)."""

from __future__ import annotations

import json
from collections.abc import Callable

from langchain_core.language_models import BaseChatModel

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
from rag_backend.agents.pov_outline_mixin import PovOutlineMixin, parse_pov_outline
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
from rag_backend.domain.constants.pov_prompts import (
    RADAR_PROMPT_DOMAIN,
    RADAR_PROMPT_OUTLINE,
    RADAR_PROMPT_VERSION,
)
from rag_backend.domain.models.pov_prompts import (
    PovHookRequest,
    PovOutlineRequest,
    PovThesis,
    SlidePolicyContext,
)
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.llm.json_utils import extract_json
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


def _outline_instruction(
    sizing: SlidePolicyContext | None,
) -> InstructionContextRequest:
    """The outline instruction request, sized to the project's contract."""
    if sizing is None:
        return InstructionContextRequest(
            phase=PHASE_OUTLINE, locale="pt", prompt_version=CAROUSEL_PROMPT_VERSION_V3
        )
    return InstructionContextRequest(
        phase=PHASE_OUTLINE,
        locale="pt",
        prompt_version=CAROUSEL_PROMPT_VERSION_V3,
        policy_version=sizing.policy_version,
        slide_count=sizing.slide_count,
    )


class OutlineAgent(PovOutlineMixin):
    """Generates human-editable carousel outlines (AE-0375: and POV outlines)."""

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
        *,
        sizing: SlidePolicyContext | None = None,
    ) -> list[dict[str, object]]:
        """Generate a slide-by-slide outline.

        AE-0375: ``sizing`` (role contracts) targets the project's contract and
        deck size; without it the outline keeps the default fixed contract.
        """
        topic = sanitize_llm_input(topic)
        audience = sanitize_llm_input(audience)
        brief = sanitize_llm_input(brief)
        safe_sources = "\n".join(sanitize_llm_input(s) for s in sources)

        instruction = self._instruction_loader.load(_outline_instruction(sizing))
        policy = load_presentation_policy(instruction.policy_version)
        slide_count = sizing.slide_count if sizing else policy.slide_count
        policy_context = (
            sizing.policy_context
            if sizing and sizing.policy_context
            else render_presentation_policy_context(policy)
        )
        # AE-0375: a sized (role) outline is returned raw; the caller stamps the
        # roles by position and normalizes, so the legacy 7-slide trim never runs.
        parse = parse_pov_outline if sizing else self._parse_outline
        prompt_text, _ = render_prompt(
            RADAR_PROMPT_DOMAIN,
            RADAR_PROMPT_OUTLINE,
            variables={
                # AE-0376: the v7 outline lists the contract roles in order.
                "roles": list(sizing.roles) if sizing else [],
                "topic": topic,
                "audience": audience,
                "brief": brief,
                "sources": safe_sources or "None",
                "locale": "pt",
                "phase": PHASE_OUTLINE,
                "slide_count": slide_count,
                "presentation_policy_context": policy_context,
                "persona_context": "",
                "revision_notes": "",
            },
            version=RADAR_PROMPT_VERSION if sizing else CAROUSEL_PROMPT_VERSION_V3,
        )
        full_prompt = f"{instruction.instruction}\n\n{prompt_text}"
        cached = self._cached_raw(full_prompt, parse)
        if cached is not None:
            return parse(cached)

        # AE-0330: one bad response used to fail the whole workflow — GLM 5.2
        # returned empty content live on 2026-09-14 and the phase died. Re-roll
        # an empty response, repair a malformed one, and cache only what parsed
        # (an unparseable raw cached here poisons every retry for the TTL).
        outline, raw = await ainvoke_json(
            self.llm,
            full_prompt,
            JsonRetryPolicy(
                parse=parse,
                agent="outline",
                model_id=self.model_id,
            ),
        )
        self._cache.set(full_prompt, self.model_id, raw)
        return outline

    def _cached_raw(
        self, prompt: str, parse: Callable[[str], list[dict[str, object]]]
    ) -> str | None:
        """Return a cached response only while it still parses, evicting poison.

        An entry written by an older deploy (or any response that stopped being
        parseable) is dropped so the caller falls through to a fresh LLM call
        instead of replaying the failure until the TTL expires.
        """
        cached = self._cache.get(prompt, self.model_id)
        if cached is None:
            return None
        try:
            parse(cached)
        except (ValueError, TypeError):
            self._cache.delete(prompt, self.model_id)
            logger.warning(
                "outline_poisoned_cache_evicted",
                model_id=self.model_id,
            )
            return None
        return cached

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


__all__ = [
    "OutlineAgent",
    "PovHookRequest",
    "PovOutlineRequest",
    "PovThesis",
    "SlidePolicyContext",
]
