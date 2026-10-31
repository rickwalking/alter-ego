""" "Ponto de Vista" outline and hook candidates for ``OutlineAgent``.

A mixin so ``outline_agent.py`` stays small and the editorial generators keep
importing a single agent module. Prompts live in ``carousel_pov/v1`` (and, for
``pov_news``, ``carousel_pov_news/v1``, by ``PovThesis.prompt_domain``); the model
may sharpen the owner's thesis, never invent it. Roles are NOT trusted from the
model: the caller stamps them by position from the contract afterwards.
"""

from __future__ import annotations

import json
from typing import Protocol

from langchain_core.language_models import BaseChatModel

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
from rag_backend.agents.pov_persona_context import pov_persona_context
from rag_backend.agents.pov_quote_context import quote_prompt_rows
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import PHASE_OUTLINE
from rag_backend.domain.constants.pov_prompts import (
    HOOK_CANDIDATE_COUNT,
    POV_PROMPT_HOOK,
    POV_PROMPT_HOOK_VERSION,
    POV_PROMPT_OUTLINE,
    POV_PROMPT_VERSION,
    RADAR_PROMPT_DOMAIN,
    RADAR_PROMPT_HOOK,
    RADAR_PROMPT_VERSION,
)
from rag_backend.domain.models.pov_prompts import (
    PovHookRequest,
    PovOutlineRequest,
    PovThesis,
    RadarHookRequest,
)
from rag_backend.infrastructure.llm.json_utils import extract_json

AGENT_POV_OUTLINE = "pov_outline"
AGENT_POV_HOOK = "pov_hook"
AGENT_RADAR_HOOK = "radar_hook"
KEY_CANDIDATES = "candidates"
KEY_TEXT = "text"
NO_SOURCES = "None"


class _AgentState(Protocol):
    llm: BaseChatModel
    model_id: str


def _thesis_variables(pov: PovThesis) -> dict[str, object]:
    return {
        "thesis": sanitize_llm_input(pov.thesis),
        "personal_proof": sanitize_llm_input(pov.personal_proof),
        "pov_format": pov.pov_format,
        "quotes": quote_prompt_rows(pov.quotes),
    }


def parse_pov_outline(raw: str) -> list[dict[str, object]]:
    """The model's slide list (unnormalized; roles are re-stamped later)."""
    try:
        data = extract_json(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(ERR_INVALID_JSON) from exc
    if not isinstance(data, list) or not data:
        raise TypeError(ERR_INVALID_JSON)
    return [item for item in data if isinstance(item, dict)]


def parse_hook_candidates(raw: str) -> list[str]:
    """Up to five distinct, non-empty hook texts."""
    try:
        data = extract_json(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(ERR_INVALID_JSON) from exc
    items = data.get(KEY_CANDIDATES) if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise TypeError(ERR_INVALID_JSON)
    texts: list[str] = []
    for item in items:
        text = item.get(KEY_TEXT) if isinstance(item, dict) else item
        if isinstance(text, str) and text.strip() and text.strip() not in texts:
            texts.append(text.strip())
    if not texts:
        raise TypeError(ERR_INVALID_JSON)
    return texts[:HOOK_CANDIDATE_COUNT]


class PovOutlineMixin:
    """POV outline + hook candidates; needs ``llm`` and ``model_id``."""

    async def generate_pov_outline(
        self: _AgentState, request: PovOutlineRequest
    ) -> list[dict[str, object]]:
        """Plan the POV deck in the contract's role order.

        persona_context is the project's persona, explicitly empty only when the project
        has none.
        """
        prompt, _ = render_prompt(
            request.pov.prompt_domain,
            POV_PROMPT_OUTLINE,
            variables={
                **_thesis_variables(request.pov),
                "topic": sanitize_llm_input(request.topic),
                "audience": sanitize_llm_input(request.audience),
                "brief": sanitize_llm_input(request.brief),
                "sources": "\n".join(sanitize_llm_input(s) for s in request.sources)
                or NO_SOURCES,
                "roles": list(request.roles),
                "slide_count": len(request.roles),
                "presentation_policy_context": request.policy_context,
                "phase": PHASE_OUTLINE,
                "persona_context": pov_persona_context(request.persona),
                "revision_notes": "",
            },
            version=POV_PROMPT_VERSION,
        )
        outline, _raw = await ainvoke_json(
            self.llm,
            prompt,
            JsonRetryPolicy(
                parse=parse_pov_outline, agent=AGENT_POV_OUTLINE, model_id=self.model_id
            ),
        )
        return outline

    async def hook_candidates(self: _AgentState, request: PovHookRequest) -> list[str]:
        """Five slide-1 hooks, one per formula, from the owner's thesis.

        The owner's recent openings go to the prompt as forbidden reuses, so
        consecutive carousels stop opening with the same formulas.
        """
        prompt, _ = render_prompt(
            request.pov.prompt_domain,
            POV_PROMPT_HOOK,
            variables={
                **_thesis_variables(request.pov),
                "topic": sanitize_llm_input(request.topic),
                "audience": sanitize_llm_input(request.audience),
                "recent_hooks": [
                    sanitize_llm_input(opening) for opening in request.recent_hooks
                ],
            },
            version=POV_PROMPT_HOOK_VERSION,
        )
        candidates, _raw = await ainvoke_json(
            self.llm,
            prompt,
            JsonRetryPolicy(
                parse=parse_hook_candidates,
                agent=AGENT_POV_HOOK,
                model_id=self.model_id,
            ),
        )
        return candidates

    async def radar_hook_candidates(
        self: _AgentState, request: RadarHookRequest
    ) -> list[str]:
        """Five Radar IA hooks from the brief and the sources only."""
        prompt, _ = render_prompt(
            RADAR_PROMPT_DOMAIN,
            RADAR_PROMPT_HOOK,
            variables={
                "topic": sanitize_llm_input(request.topic),
                "audience": sanitize_llm_input(request.audience),
                "brief": sanitize_llm_input(request.brief),
                "sources": "\n".join(sanitize_llm_input(s) for s in request.sources)
                or NO_SOURCES,
            },
            version=RADAR_PROMPT_VERSION,
        )
        candidates, _raw = await ainvoke_json(
            self.llm,
            prompt,
            JsonRetryPolicy(
                parse=parse_hook_candidates,
                agent=AGENT_RADAR_HOOK,
                model_id=self.model_id,
            ),
        )
        return candidates


__all__ = ["PovOutlineMixin", "parse_hook_candidates", "parse_pov_outline"]
