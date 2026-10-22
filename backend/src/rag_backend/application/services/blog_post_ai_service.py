"""Blog post AI assistance service."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.persona_agent import PersonaAgent
from rag_backend.application.services.blog.ai_envelope import (
    parse_suggestion,
    strip_code_fence,
)
from rag_backend.application.services.blog_workflow_observability import (
    StartupParams,
    blog_ai_propagate,
    start_blog_workflow_trace,
)
from rag_backend.domain.constants.blog_ai import (
    ERR_INVALID_AI_ACTION,
    PROMPT_AI_IMPROVE,
    PROMPT_AI_SUGGEST,
    SUGGEST_DEFAULT_EXPLANATION,
    VALID_AI_ACTIONS,
)
from rag_backend.domain.constants.blog_document import BLOG_SECTION_MAX_CHARS
from rag_backend.domain.constants.blog_editor import (
    ERR_BLOG_PERSONA_REQUIRED,
    ERR_BLOG_REWRITE_EMPTY,
    ERR_BLOG_REWRITE_TOO_LONG,
    PHASE_BLOG_SECTION_REWRITE,
    REWRITE_NO_HEADING_INSTRUCTION,
)
from rag_backend.domain.constants.input_sanitizer import MAX_LLM_INPUT_LENGTH
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.database.models import PersonaProfileModel


@dataclass(frozen=True)
class BlogAiTraceContext:
    """Trace metadata for blog AI Langfuse observability."""

    post_id: str = ""
    user_id: str = "system"


def _start_action_trace(
    action: str, trace: BlogAiTraceContext | None
) -> BlogAiTraceContext:
    if action not in VALID_AI_ACTIONS:
        raise ValueError(ERR_INVALID_AI_ACTION)
    trace_context = trace or BlogAiTraceContext()
    start_blog_workflow_trace(
        StartupParams(
            post_id=trace_context.post_id or "unknown",
            user_id=trace_context.user_id,
        )
    )
    return trace_context


@dataclass
class _SuggestInput:
    """Bundled input for BlogPostAIService.suggest()."""

    text: str
    action: str
    context: str | None = None
    trace: BlogAiTraceContext | None = None


@dataclass
class _ImproveInput:
    """Bundled input for BlogPostAIService.improve()."""

    db: AsyncSession
    text: str
    action: str
    context: str | None = None
    persona_id: str | None = None
    trace: BlogAiTraceContext | None = None


@dataclass
class _RewriteInput:
    """Bundled input for BlogPostAIService.rewrite_section().

    persona_id is the requested persona, else the post's carousel persona (resolved by
    the route); None falls back to the first (single-author) persona.
    """

    db: AsyncSession
    body_md: str
    heading: str | None = None
    persona_id: str | None = None
    trace: BlogAiTraceContext | None = None


class LLMServiceProtocol(Protocol):
    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str: ...

    @property
    def chat_model(self) -> BaseChatModel: ...


class BlogPostAIService:
    """AI suggestions, improvements and section rewrites for blog posts.

    Images go through ``BlogImageService``; the legacy
    ``generate_image`` path was removed with ``POST /generate-image``.
    """

    def __init__(self, llm_service: LLMServiceProtocol) -> None:
        self._llm_service = llm_service

    async def suggest(
        self,
        input_data: _SuggestInput,
    ) -> dict[str, str]:
        """Generate an AI suggestion for blog text.

        Fenced or nested envelopes become plain text.
        """
        trace_context = _start_action_trace(input_data.action, input_data.trace)
        safe_text = sanitize_llm_input(input_data.text)
        safe_context = sanitize_llm_input(input_data.context or "")
        with blog_ai_propagate(trace_context.post_id or "unknown", "ai_suggest"):
            prompt = PROMPT_AI_SUGGEST.format(
                action=input_data.action,
                context=safe_context,
                text=safe_text,
            )
            raw = await self._llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
        parsed = parse_suggestion(raw or "")
        return {
            "original_text": safe_text,
            "suggested_text": parsed.text,
            "suggestion_type": input_data.action,
            "explanation": (
                SUGGEST_DEFAULT_EXPLANATION.format(action=input_data.action)
                if parsed.explanation is None
                else parsed.explanation
            ),
        }

    async def improve(
        self,
        input_data: _ImproveInput,
    ) -> dict[str, str]:
        """Improve selected blog text, optionally enforcing a persona voice."""
        trace_context = _start_action_trace(input_data.action, input_data.trace)
        safe_text = sanitize_llm_input(input_data.text)
        safe_context = sanitize_llm_input(input_data.context or "")

        with blog_ai_propagate(trace_context.post_id or "unknown", "ai_improve"):
            persona = await self._load_persona(input_data.db, input_data.persona_id)
            if persona is not None:
                agent = PersonaAgent(persona=persona, llm=self._llm_service.chat_model)
                improved = await agent.enforce(safe_text, context=safe_context)
                return {
                    "original_text": safe_text,
                    "improved_text": improved,
                    "action": input_data.action,
                }

            prompt = PROMPT_AI_IMPROVE.format(
                action=input_data.action,
                context=safe_context,
                text=safe_text,
            )
            improved = await self._llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
        return {
            "original_text": safe_text,
            "improved_text": improved.strip(),
            "action": input_data.action,
        }

    async def rewrite_section(self, input_data: _RewriteInput) -> str:
        """One section body rewritten in the persona voice (``PersonaAgent.enforce``).

        Persona: the given one, else the first (single-author) persona; none at
        all is a ``ValueError``. The model OUTPUT is not run through the input
        sanitizer (it strips ``( ) < >`` and truncates): only a surrounding code
        fence is removed and the length is checked against the section limit;
        rendering relies on the markdown allow-list. A body longer than the LLM
        input limit is refused instead of being silently truncated.

        The model is told not to repeat the section heading and
        a leading heading echo (bold, ``#`` or plain line equal to the heading)
        is stripped from the result, so the heading is never duplicated into
        the stored body.
        """
        if len(input_data.body_md) > MAX_LLM_INPUT_LENGTH:
            raise ValueError(ERR_BLOG_REWRITE_TOO_LONG)
        persona = await self._resolve_persona(input_data)
        if persona is None:
            raise ValueError(ERR_BLOG_PERSONA_REQUIRED)
        post_id = (input_data.trace or BlogAiTraceContext()).post_id or "unknown"
        agent = PersonaAgent(persona=persona, llm=self._llm_service.chat_model)
        context = _rewrite_context(input_data.heading)
        with blog_ai_propagate(post_id, PHASE_BLOG_SECTION_REWRITE):
            rewritten = await agent.enforce(input_data.body_md, context=context)
        return _checked_rewrite(strip_heading_echo(rewritten, input_data.heading))

    async def _resolve_persona(
        self, input_data: _RewriteInput
    ) -> PersonaProfile | None:
        db = input_data.db
        if input_data.persona_id is not None:
            return await self._load_persona(db, input_data.persona_id)
        result = await db.execute(
            select(PersonaProfileModel)
            .order_by(PersonaProfileModel.created_at)
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model is not None else None

    @staticmethod
    async def _load_persona(
        db: AsyncSession,
        persona_id: str | None,
    ) -> PersonaProfile | None:
        if persona_id is None:
            return None
        model = await db.get(PersonaProfileModel, persona_id)
        if model is None:
            return None
        return model.to_entity()


def _checked_rewrite(rewritten: object) -> str:
    text = strip_code_fence(rewritten if isinstance(rewritten, str) else "")
    if not text:
        raise ValueError(ERR_BLOG_REWRITE_EMPTY)
    if len(text) > BLOG_SECTION_MAX_CHARS:
        raise ValueError(ERR_BLOG_REWRITE_TOO_LONG)
    return text


def _rewrite_context(heading: str | None) -> str:
    """The persona context: the section heading plus the no-heading instruction."""
    if not heading:
        return REWRITE_NO_HEADING_INSTRUCTION
    return f"{heading}\n\n{REWRITE_NO_HEADING_INSTRUCTION}"


_HEADING_BOLD_RE = re.compile(r"^\*\*(.+?)\*\*$", flags=re.DOTALL)
_HEADING_EMPHASIS_RE = re.compile(r"^[_\*](.+?)[_\*]$", flags=re.DOTALL)


def _normalize_heading(text: str) -> str:
    """A heading with markers and case differences removed (F-08 echo match)."""
    stripped = text.strip().lstrip("#").strip()
    for pattern in (_HEADING_BOLD_RE, _HEADING_EMPHASIS_RE):
        match = pattern.match(stripped)
        if match is not None:
            stripped = match.group(1).strip()
            break
    return re.sub(r"\s+", " ", stripped).casefold()


def strip_heading_echo(body: object, heading: str | None) -> str:
    """Remove a leading echo of the section heading from a rewrite result.

    The model sometimes repeats the heading (``**H**``, ``# H`` or a plain line)
    as the first line of the rewritten body (QA F-08). Leading blank lines are
    skipped, then a first line that normalizes to the heading is dropped. A body
    that starts differently is returned untouched. A non-string result degrades
    to the empty string like the length check does.
    """
    text = body if isinstance(body, str) else ""
    if not heading:
        return text
    expected = _normalize_heading(heading)
    if not expected:
        return text
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and _normalize_heading(lines[0]) == expected:
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines)


__all__ = ["BlogPostAIService"]
