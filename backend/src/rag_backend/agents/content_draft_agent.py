"""Content draft agent with persona enforcement (AI-008).

DRAFT_QUOTE_ID_KEY lets a pov_news slide pick a verified quote by id, never by its text.
"""

from __future__ import annotations

import copy
import json

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable

from rag_backend.agents.carousel_rubric_judge import render_rubric_criteria
from rag_backend.agents.input_sanitizer import (
    sanitize_display_input,
    sanitize_model_copy,
)
from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.agents.pov_quote_context import quote_prompt_rows
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.instruction_context_loader import (
    CarouselInstructionContextLoader,
    InstructionContextRequest,
)
from rag_backend.application.services.carousel.presentation_policy import (
    RUBRIC_AUDIENCE_CONTENT,
    load_presentation_policy,
    render_presentation_policy_context,
    render_quality_rubric,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel import CAROUSEL_PROMPT_VERSION_V6
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
from rag_backend.domain.constants.news_quotes import CARD_KEY_QUOTE_ID
from rag_backend.domain.constants.pov_prompts import (
    POV_PROMPT_CONTENT,
    POV_PROMPT_VERSION,
    RADAR_PROMPT_CONTENT,
    RADAR_PROMPT_DOMAIN,
    RADAR_PROMPT_VERSION,
)
from rag_backend.domain.constants.presentation_policy import (
    CREATE_TIME_PRESENTATION_POLICY_VERSION,
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.models.carousel_rubric import CarouselRubric
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.domain.models.pov_prompts import SlidePolicyContext
from rag_backend.infrastructure.cache.ai_response_cache import get_ai_response_cache
from rag_backend.infrastructure.llm.json_utils import extract_json
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

LOG_LONG_FORM_NOTES_MISSING = "content_draft.long_form_notes_missing"
DRAFT_QUOTE_ID_KEY = CARD_KEY_QUOTE_ID
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


def _render_content_prompt(
    variables: dict[str, object], slide_policy: SlidePolicyContext | None
) -> tuple[str, dict[str, object]]:
    """v6 content (fixed contracts), v7 per role (Radar IA v4), or
    the POV prompt from the owner's thesis."""
    if slide_policy is None:
        return render_prompt(
            "carousel",
            "content",
            variables=variables,
            version=CAROUSEL_PROMPT_VERSION_V6,
        )
    pov = slide_policy.pov
    if pov is None:
        return render_prompt(
            RADAR_PROMPT_DOMAIN,
            RADAR_PROMPT_CONTENT,
            variables={
                **variables,
                "role": slide_policy.role,
                "hook_text": sanitize_model_copy(slide_policy.hook_text),
            },
            version=RADAR_PROMPT_VERSION,
        )
    return render_prompt(
        pov.pov.prompt_domain,
        POV_PROMPT_CONTENT,
        variables={
            **variables,
            "role": pov.role,
            "slide_count": pov.slide_count,
            "thesis": sanitize_model_copy(pov.pov.thesis),
            "personal_proof": sanitize_model_copy(pov.pov.personal_proof),
            "pov_format": pov.pov.pov_format,
            "hook_text": sanitize_model_copy(pov.hook_text),
            "cta_copy": pov.cta_copy,
            "quotes": quote_prompt_rows(pov.pov.quotes),
        },
        version=POV_PROMPT_VERSION,
    )


def agent_for_rubric(
    agent: ContentDraftAgent, rubric: CarouselRubric | None
) -> ContentDraftAgent:
    """``agent`` drafting against ``rubric``; no rubric leaves it untouched."""
    return agent if rubric is None else agent.with_rubric(rubric)


class ContentDraftAgent:
    """Drafts carousel slide copy with optional persona enforcement."""

    def __init__(self, llm: BaseChatModel, model_id: str = "content-draft") -> None:
        self.llm = llm
        self.model_id = model_id
        self._cache = get_ai_response_cache()
        self._instruction_loader = CarouselInstructionContextLoader()
        self._prompt_version = CAROUSEL_PROMPT_VERSION_V6
        self._rubric_block = ""

    def with_rubric(self, rubric: CarouselRubric | None) -> ContentDraftAgent:
        """This agent with the carousel's quality ``rubric`` appended to every prompt
        it drafts; no rubric keeps this agent. A copy, so one project's rubric never
        reaches another project's drafts.
        """
        if rubric is None or not rubric.criteria:
            return self
        scoped = copy.copy(self)
        scoped._rubric_block = render_rubric_criteria(rubric)
        return scoped

    def _full_prompt(self, instruction: str, prompt_text: str) -> str:
        """The instruction, the content prompt and the rubric block (when set)."""
        parts = [instruction, prompt_text, self._rubric_block]
        return "\n\n".join(part for part in parts if part)

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
        policy: SlidePolicyContext | None = None,
    ) -> dict[str, object]:
        """Draft copy for a single slide.

        ``policy`` (role contracts) targets the project's contract and
        deck size; with ``policy.pov`` the slide is drafted from the owner's
        thesis with the ``carousel_pov/v1`` prompt.

        Titles and key points use case-preserving sanitization: lowercased input made
        the model echo lowercase copy into the slides. Revision notes are rendered once,
        in the instruction context. The quality rubric is the current contract's (the
        project's own when it is a role contract). The YAML model config (temperature,
        max_tokens) is applied through a per-call bind. An empty response is re-rolled,
        a malformed one repaired, and only what parsed is cached, since an unparseable
        raw would poison every retry for the cache TTL.
        """
        title = sanitize_model_copy(title)
        safe_points = [sanitize_model_copy(p) for p in key_points]
        persona_context = sanitize_display_input(persona_context)
        revision_notes = sanitize_display_input(revision_notes)
        sibling_context = sanitize_model_copy(sibling_context)
        previous_draft = sanitize_model_copy(previous_draft)

        instruction = self._instruction_loader.load(
            InstructionContextRequest(
                phase=PHASE_CONTENT,
                locale=locale,
                persona_context=persona_context,
                revision_notes=revision_notes,
                slide_number=slide_index,
                prompt_version=CAROUSEL_PROMPT_VERSION_V6,
                sibling_context=sibling_context,
                previous_draft=previous_draft,
                policy_version=policy.policy_version
                if policy
                else (DEFAULT_PRESENTATION_POLICY_VERSION),
                slide_count=policy.slide_count if policy else None,
            )
        )
        rubric_version = (
            policy.policy_version if policy else CREATE_TIME_PRESENTATION_POLICY_VERSION
        )
        slide_policy = policy
        policy = load_presentation_policy(instruction.policy_version)
        variables: dict[str, object] = {
            "slide_number": slide_index,
            "title": title,
            "key_points": ", ".join(safe_points),
            "locale": locale,
            "phase": PHASE_CONTENT,
            "presentation_policy_context": (
                slide_policy.policy_context
                if slide_policy and slide_policy.policy_context
                else render_presentation_policy_context(policy)
            ),
            "persona_context": persona_context or "Default professional voice.",
            "quality_rubric": render_quality_rubric(
                load_presentation_policy(rubric_version), RUBRIC_AUDIENCE_CONTENT
            ),
        }
        prompt_text, model_cfg = _render_content_prompt(variables, slide_policy)
        full_prompt = self._full_prompt(instruction.instruction, prompt_text)
        cached = self._cached_raw(full_prompt)
        if cached is not None:
            draft = self._parse_draft(cached)
        else:
            runnable = self._runnable_with_model_config(model_cfg)
            draft, raw = await ainvoke_json(
                runnable,
                full_prompt,
                JsonRetryPolicy(
                    parse=self._parse_draft,
                    agent="content_draft",
                    model_id=self.model_id,
                    run_detail=f"slide {slide_index}",
                ),
            )
            self._cache.set(full_prompt, self.model_id, raw)
        self._warn_if_notes_missing(draft, slide_index)
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
        """Bind supported sampling knobs from the prompt YAML model block."""
        bind_kwargs = _model_bind_kwargs(model_cfg)
        if not bind_kwargs:
            return self.llm
        return self.llm.bind(**bind_kwargs)

    def _parse_draft(self, raw: str) -> dict[str, object]:
        """Parse a draft response and sanitize its long-form notes.

        The notes are sanitized case-preserving at the source because they later feed
        the translation prompt and the public blog verbatim.
        """
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
        quote_id = data.get(DRAFT_QUOTE_ID_KEY)
        if isinstance(quote_id, str) and quote_id.strip():
            draft[DRAFT_QUOTE_ID_KEY] = quote_id.strip()
        icon_name = data.get("icon_name")
        if isinstance(icon_name, str) and icon_name.strip():
            draft["icon_name"] = icon_name.strip()
        long_form_notes = data.get("long_form_notes")
        if isinstance(long_form_notes, str) and long_form_notes.strip():
            draft["long_form_notes"] = sanitize_display_input(long_form_notes)
        return draft

    def _warn_if_notes_missing(
        self, draft: dict[str, object], slide_index: int
    ) -> None:
        """A note-less reply silently reproduces the H1-only blog section.

        Fires once per drafted slide (not per parse) with enough context for ops
        to correlate the affected slide.
        """
        if "long_form_notes" in draft:
            return
        logger.warning(
            LOG_LONG_FORM_NOTES_MISSING,
            slide_index=slide_index,
            model_id=self.model_id,
            prompt_version=self._prompt_version,
        )


__all__ = ["ContentDraftAgent", "agent_for_rubric"]
