"""BlogWriterAgent — the blog writer façade (AE-0425, ADR-0025, ADR-0016).

Implements the ``BlogArticleWriter`` port. Model routing (ADR-0014):

* drafting, PT/EN copy and the rewrite pass → the **fast** model,
* the quality judgement that steers the rewrite → the **reasoning** model,

each a role-routed model that already falls back to ``LLM_MODEL_FALLBACK`` on
error/timeout/empty, with ``ainvoke_json`` re-rolling, repairing and falling
back on bad JSON. Every source (research, notes, outline, URLs, persona
samples) is sanitized and fenced as data in the prompt.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import structlog
from langchain_core.language_models import BaseChatModel

from rag_backend.agents.blog_writer.constants import (
    AGENT_DRAFT,
    AGENT_JUDGE,
    AGENT_REWRITE,
    ERR_WRITER_FAILED,
    LANGUAGE_NAMES,
    LOG_JUDGE_FAILED,
    MAX_NOTE_CHARS,
    MAX_OUTLINE_ITEMS,
    MAX_RESEARCH_ITEM_CHARS,
    MAX_RESEARCH_ITEMS,
    MAX_SOURCE_URLS,
    PROMPT_DOMAIN,
    PROMPT_DRAFT,
    PROMPT_JUDGE,
    PROMPT_REWRITE,
    PROMPT_VERSION,
)
from rag_backend.agents.blog_writer.parsing import (
    parse_draft,
    parse_notes,
    parse_rewrite,
)
from rag_backend.agents.blog_writer.persona_block import persona_variables
from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.llm_json_retry import JsonRetryPolicy, ainvoke_json
from rag_backend.agents.prompts.registry import get_system_prompt, render_prompt
from rag_backend.domain.constants.blog_voice import (
    BANNED_PHRASES_EN,
    BANNED_PHRASES_PT,
    VOICE_SCORE_THRESHOLD,
)
from rag_backend.domain.models.blog_generation import (
    DraftArticle,
    DraftSection,
    JudgeRequest,
    RewriteRequest,
    WriterBrief,
    WriterFailedError,
)

T = TypeVar("T")

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BlogWriterModels:
    """The role-routed chat models the writer uses."""

    fast: BaseChatModel
    reasoning: BaseChatModel


def _clean_all(values: tuple[str, ...], limits: tuple[int, int]) -> list[str]:
    count, chars = limits
    cleaned = (sanitize_llm_input(value)[:chars] for value in values[:count])
    return [value for value in cleaned if value]


def _outline(brief: WriterBrief) -> list[dict[str, object]]:
    return [
        {
            "title": sanitize_llm_input(point.title),
            "key_points": [sanitize_llm_input(item) for item in point.key_points],
        }
        for point in brief.outline[:MAX_OUTLINE_ITEMS]
    ]


def draft_variables(brief: WriterBrief) -> dict[str, object]:
    """Template variables of the draft prompt (all sources sanitized)."""
    return {
        "system": get_system_prompt(PROMPT_DOMAIN, version=PROMPT_VERSION),
        "persona": persona_variables(brief.persona),
        "title": sanitize_llm_input(brief.title),
        "topic": sanitize_llm_input(brief.topic),
        "research": _clean_all(
            brief.research, (MAX_RESEARCH_ITEMS, MAX_RESEARCH_ITEM_CHARS)
        ),
        "outline": _outline(brief),
        "notes": _clean_all(brief.notes, (len(brief.notes), MAX_NOTE_CHARS)),
        "source_urls": _clean_all(brief.source_urls, (MAX_SOURCE_URLS, MAX_NOTE_CHARS)),
        "section_count": brief.section_count,
        "roles": list(brief.section_roles),
        "banned_pt": list(BANNED_PHRASES_PT),
        "banned_en": list(BANNED_PHRASES_EN),
    }


def _sections_data(sections: tuple[DraftSection, ...]) -> list[dict[str, object]]:
    return [
        {"heading": section.heading, "body_md": section.body_md} for section in sections
    ]


class BlogWriterAgent:
    """Drafts, judges and rewrites one blog article (``BlogArticleWriter``)."""

    def __init__(self, models: BlogWriterModels) -> None:
        self._models = models

    async def draft(self, brief: WriterBrief) -> DraftArticle:
        """ONE continuous PT article + its EN translation (fast model)."""
        prompt = render_prompt(
            PROMPT_DOMAIN, PROMPT_DRAFT, draft_variables(brief), version=PROMPT_VERSION
        )[0]
        return await self._json(self._models.fast, prompt, (parse_draft, AGENT_DRAFT))

    async def rewrite(self, request: RewriteRequest) -> tuple[DraftSection, ...]:
        """The single rewrite pass of one language (fast model)."""
        variables: dict[str, object] = {
            "system": get_system_prompt(PROMPT_DOMAIN, version=PROMPT_VERSION),
            "persona": persona_variables(request.brief.persona),
            "language": request.language,
            "language_name": LANGUAGE_NAMES.get(request.language, request.language),
            "section_count": request.brief.section_count,
            "roles": list(request.brief.section_roles),
            "notes": [sanitize_llm_input(note) for note in request.notes],
            "sections": _sections_data(request.sections),
        }
        prompt = render_prompt(
            PROMPT_DOMAIN, PROMPT_REWRITE, variables, version=PROMPT_VERSION
        )[0]
        return await self._json(
            self._models.fast, prompt, (parse_rewrite, AGENT_REWRITE)
        )

    async def judge(self, request: JudgeRequest) -> tuple[str, ...]:
        """Reasoning-model revision notes; best-effort (``()`` on failure)."""
        suggestions = request.voice.breakdown.get("suggestions", [])
        variables: dict[str, object] = {
            "language_name": LANGUAGE_NAMES.get(request.language, request.language),
            "voice_score": round(request.voice.overall, 1),
            "threshold": VOICE_SCORE_THRESHOLD,
            "repeated": list(request.findings.repeated_sentences),
            "banned": list(request.findings.banned_phrases),
            "english": list(request.findings.english_sections),
            "suggestions": suggestions if isinstance(suggestions, list) else [],
            "sections": _sections_data(request.sections),
        }
        prompt = render_prompt(
            PROMPT_DOMAIN, PROMPT_JUDGE, variables, version=PROMPT_VERSION
        )[0]
        try:
            return await self._json(
                self._models.reasoning, prompt, (parse_notes, AGENT_JUDGE)
            )
        except WriterFailedError:
            logger.warning(LOG_JUDGE_FAILED, language=request.language)
            return ()

    @staticmethod
    async def _json(
        model: BaseChatModel, prompt: str, parser: tuple[Callable[[str], T], str]
    ) -> T:
        parse, agent = parser
        policy = JsonRetryPolicy(parse=parse, agent=agent, model_id=agent)
        try:
            parsed, _raw = await ainvoke_json(model, prompt, policy)
        except Exception as exc:
            raise WriterFailedError(ERR_WRITER_FAILED.format(reason=str(exc))) from exc
        return parsed


__all__ = ["BlogWriterAgent", "BlogWriterModels", "draft_variables"]
