"""PT -> EN translation of a blog document (AE-0424 "Generate EN translation").

The editor's EN tab is read-only until ``content.translations.en`` exists; this
service builds it from the PT document, one section per (bounded-concurrency)
LLM call, keeping each section's image and the cover (the same art serves both
languages). Every EN section gets a fresh id. Any failed section fails the
whole translation (nothing is stored), so EN is never half-written, and so
does a section the model answered in Portuguese (AE-0435: the carousel's
``wrong_language`` detector, no model), so EN is never Portuguese.

The owner's own text is delimited as data in the versioned template
(``agents/prompts/blog/v1/translate_section.yaml``); it is not passed through
``sanitize_llm_input``, which would strip markdown link parentheses.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from typing import Protocol

from rag_backend.application.services.blog.ai_envelope import strip_code_fence
from rag_backend.application.services.blog_workflow_observability import (
    blog_ai_propagate,
)
from rag_backend.application.services.carousel.copy_hygiene_text import (
    wrong_language_detail,
)
from rag_backend.domain.constants.blog_document import (
    BLOG_SCHEMA_V2,
    BLOG_SECTION_ID_PREFIX,
    KEY_BODY_MD,
    KEY_HEADING,
    KEY_SCHEMA,
)
from rag_backend.domain.constants.blog_editor import (
    ERR_BLOG_TRANSLATION_FAILED,
    ERR_BLOG_TRANSLATION_WRONG_LANGUAGE,
    PHASE_BLOG_TRANSLATION,
)
from rag_backend.domain.models.blog_document import (
    BlogLanguageDocument,
    BlogSection,
)

TRANSLATION_CONCURRENCY = 4
TRANSLATION_TEMPERATURE = 0.2


class TranslationLLM(Protocol):
    """The text-generation port the translation uses."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str: ...


class BlogTranslationError(RuntimeError):
    """The translation could not be produced; ``code`` is the API detail."""

    def __init__(self, code: str = ERR_BLOG_TRANSLATION_FAILED) -> None:
        super().__init__(code)
        self.code = code


def _parse_answer(raw: str) -> tuple[str | None, str]:
    try:
        data = json.loads(strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise BlogTranslationError from exc
    body = data.get(KEY_BODY_MD) if isinstance(data, dict) else None
    if not isinstance(body, str) or not body.strip():
        raise BlogTranslationError
    heading = data.get(KEY_HEADING)
    return (heading.strip() or None) if isinstance(heading, str) else None, body


SectionPromptRenderer = Callable[[str | None, str], str]


class BlogTranslationService:
    """Translate the PT sections into a ``translations.en`` document.

    ``render_prompt(heading, body_md)`` renders the versioned translation
    template (injected: ``agents.blog_editor_prompts.translate_section_prompt``).
    """

    def __init__(
        self, llm: TranslationLLM, render_prompt: SectionPromptRenderer
    ) -> None:
        self._llm = llm
        self._render_prompt = render_prompt
        self._limit = asyncio.Semaphore(TRANSLATION_CONCURRENCY)

    async def translate(
        self, post_id: str, source: BlogLanguageDocument
    ) -> BlogLanguageDocument:
        """The EN document; raises :class:`BlogTranslationError` on any failure."""
        with blog_ai_propagate(post_id, PHASE_BLOG_TRANSLATION):
            sections = await asyncio.gather(
                *(self._section(section) for section in source.sections)
            )
        return BlogLanguageDocument.model_validate({
            KEY_SCHEMA: BLOG_SCHEMA_V2,
            "cover": source.cover,
            "sections": sections,
            "quality": None,
        })

    async def _section(self, section: BlogSection) -> BlogSection:
        if not section.body_md.strip():
            return section.model_copy(update={"id": _new_id()})
        prompt = self._render_prompt(section.heading, section.body_md)
        async with self._limit:
            try:
                raw = await self._llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=TRANSLATION_TEMPERATURE,
                )
            except Exception as exc:
                raise BlogTranslationError from exc
        heading, body = _parse_answer(raw or "")
        if wrong_language_detail(f"{heading or ''}\n{body}", portuguese=False):
            raise BlogTranslationError(ERR_BLOG_TRANSLATION_WRONG_LANGUAGE)
        return BlogSection(
            id=_new_id(),
            heading=heading if section.heading else None,
            body_md=body,
            image=section.image,
        )


def _new_id() -> str:
    return f"{BLOG_SECTION_ID_PREFIX}{uuid.uuid4()}"


__all__ = [
    "BlogTranslationError",
    "BlogTranslationService",
    "SectionPromptRenderer",
    "TranslationLLM",
]
