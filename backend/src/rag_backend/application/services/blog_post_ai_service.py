"""Blog post AI assistance service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.input_sanitizer import (
    sanitize_display_input,
    sanitize_llm_input,
)
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
    ERR_IMAGE_GENERATION_FAILED,
    ERR_INVALID_AI_ACTION,
    PROMPT_AI_IMPROVE,
    PROMPT_AI_SUGGEST,
    SUGGEST_DEFAULT_EXPLANATION,
    VALID_AI_ACTIONS,
)
from rag_backend.domain.constants.blog_editor import (
    ERR_BLOG_PERSONA_REQUIRED,
    ERR_BLOG_REWRITE_EMPTY,
    PHASE_BLOG_SECTION_REWRITE,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.domain.protocols import ImageGenerationService
from rag_backend.infrastructure.database.models import (
    CarouselProjectModel,
    PersonaProfileModel,
)


@dataclass(frozen=True)
class BlogAiTraceContext:
    """Trace metadata for blog AI Langfuse observability."""

    post_id: str = ""
    user_id: str = "system"


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
    """Bundled input for BlogPostAIService.rewrite_section() (AE-0424)."""

    db: AsyncSession
    body_md: str
    heading: str | None = None
    persona_id: str | None = None
    project_id: str | None = None
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
    """Provides AI suggestions, improvements, and image generation for blog posts."""

    def __init__(
        self,
        llm_service: LLMServiceProtocol,
        image_service: ImageGenerationService | None,
        output_dir: Path,
    ) -> None:
        self._llm_service = llm_service
        self._image_service = image_service
        self._output_dir = output_dir

    async def suggest(
        self,
        input_data: _SuggestInput,
    ) -> dict[str, str]:
        """Generate an AI suggestion for blog text."""
        if input_data.action not in VALID_AI_ACTIONS:
            raise ValueError(ERR_INVALID_AI_ACTION)

        trace_context = input_data.trace or BlogAiTraceContext()
        start_blog_workflow_trace(
            StartupParams(
                post_id=trace_context.post_id or "unknown",
                user_id=trace_context.user_id,
            )
        )
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
        # AE-0424 (F-10): fenced/nested envelopes become plain text.
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
        if input_data.action not in VALID_AI_ACTIONS:
            raise ValueError(ERR_INVALID_AI_ACTION)

        trace_context = input_data.trace or BlogAiTraceContext()
        start_blog_workflow_trace(
            StartupParams(
                post_id=trace_context.post_id or "unknown",
                user_id=trace_context.user_id,
            )
        )
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

    async def generate_image(
        self,
        post_id: str,
        prompt: str,
        *,
        user_id: str = "system",
    ) -> dict[str, str]:
        """Generate a featured image for a blog post."""
        if self._image_service is None:
            raise RuntimeError(
                ERR_IMAGE_GENERATION_FAILED.format(reason="image service unavailable")
            )

        start_blog_workflow_trace(StartupParams(post_id=post_id, user_id=user_id))
        safe_prompt = sanitize_llm_input(prompt)
        output_dir = self._output_dir / post_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid.uuid4()}.jpg"

        with blog_ai_propagate(post_id, "generate_image"):
            try:
                await self._image_service.generate_image(safe_prompt, str(output_path))
            except Exception as exc:
                raise RuntimeError(
                    ERR_IMAGE_GENERATION_FAILED.format(reason=str(exc))
                ) from exc

        return {
            "prompt": safe_prompt,
            "image_url": str(output_path),
        }

    async def rewrite_section(self, input_data: _RewriteInput) -> str:
        """One section body rewritten in the persona voice (``PersonaAgent.enforce``).

        Persona: the requested one, else the carousel project's, else the
        first (single-author) persona; none at all is a ``ValueError``.
        """
        persona = await self._resolve_persona(input_data)
        if persona is None:
            raise ValueError(ERR_BLOG_PERSONA_REQUIRED)
        post_id = (input_data.trace or BlogAiTraceContext()).post_id or "unknown"
        agent = PersonaAgent(persona=persona, llm=self._llm_service.chat_model)
        with blog_ai_propagate(post_id, PHASE_BLOG_SECTION_REWRITE):
            rewritten = await agent.enforce(
                input_data.body_md, context=input_data.heading or ""
            )
        text = sanitize_display_input(strip_code_fence(rewritten or ""))
        if not text:
            raise ValueError(ERR_BLOG_REWRITE_EMPTY)
        return text

    async def _resolve_persona(
        self, input_data: _RewriteInput
    ) -> PersonaProfile | None:
        db = input_data.db
        persona_id = input_data.persona_id or await _project_persona_id(
            db, input_data.project_id
        )
        if persona_id is not None:
            return await self._load_persona(db, persona_id)
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


async def _project_persona_id(db: AsyncSession, project_id: str | None) -> str | None:
    if project_id is None:
        return None
    project = await db.get(CarouselProjectModel, project_id)
    persona_id = getattr(project, "persona_id", None)
    return str(persona_id) if persona_id else None


__all__ = ["BlogPostAIService"]
