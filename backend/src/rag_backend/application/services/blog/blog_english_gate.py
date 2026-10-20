"""The deterministic EN language gate of a generated article (AE-0435).

Prod 2026-10-19/20 stored Portuguese as ``translations.en`` (posts ba37f6f9 and
99886e71) with an EN voice score of 85: the voice gate never checked the
language. This gate runs after the EN quality gate, without any model:

1. every EN section (heading + body) is checked with the carousel's
   ``wrong_language`` detector (:func:`portuguese_sections`);
2. if any reads as Portuguese, the gated PT article is retranslated with the
   editor's PT -> EN translation (AE-0424), at most ``max_retranslations``
   times; a failed call counts as one attempt;
3. an English retranslation is scored + scanned like any EN article and kept;
   if none is English, the gate returns ``None`` and the run stores the
   article WITHOUT ``translations.en`` (never Portuguese as English).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import structlog

from rag_backend.application.services.blog.blog_quality_gate import (
    BlogQualityGate,
    GateCommand,
)
from rag_backend.application.services.blog.blog_quality_scan import (
    portuguese_sections,
)
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationError,
)
from rag_backend.domain.constants.blog_document import (
    BLOG_SCHEMA_V2,
    BLOG_SECTION_ID_PREFIX,
    KEY_SCHEMA,
)
from rag_backend.domain.constants.blog_generation import (
    BLOG_EN_MAX_RETRANSLATIONS,
    LANGUAGE_EN,
    LOG_EN_RETRANSLATION_FAILED,
    LOG_EN_WRONG_LANGUAGE,
)
from rag_backend.domain.models.blog_document import BlogLanguageDocument
from rag_backend.domain.models.blog_generation import (
    DraftSection,
    GatedLanguage,
    WriterBrief,
)
from rag_backend.domain.protocols.blog_generation import BlogDocumentTranslator

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class EnglishGateDeps:
    """The PT -> EN translator, the quality gate (to score a retranslation)
    and the retry bound."""

    translator: BlogDocumentTranslator
    gate: BlogQualityGate
    max_retranslations: int = BLOG_EN_MAX_RETRANSLATIONS


@dataclass(frozen=True)
class EnglishCheck:
    """Both gated languages of one post and the brief they were written for."""

    post_id: str
    pt: GatedLanguage
    en: GatedLanguage
    brief: WriterBrief


def as_language_document(sections: tuple[DraftSection, ...]) -> BlogLanguageDocument:
    """``sections`` as an image-less document (placeholder ids) to translate."""
    return BlogLanguageDocument.model_validate({
        KEY_SCHEMA: BLOG_SCHEMA_V2,
        "sections": [
            {
                "id": f"{BLOG_SECTION_ID_PREFIX}{index}",
                "heading": section.heading,
                "body_md": section.body_md,
            }
            for index, section in enumerate(sections)
        ],
    })


def as_draft_sections(document: BlogLanguageDocument) -> tuple[DraftSection, ...]:
    """The heading + body of every section of ``document``."""
    return tuple(
        DraftSection(heading=section.heading, body_md=section.body_md)
        for section in document.sections
    )


class EnglishLanguageGate:
    """Keeps an English EN, repairs a Portuguese one, or returns ``None``."""

    def __init__(self, deps: EnglishGateDeps) -> None:
        self._deps = deps

    async def ensure(self, check: EnglishCheck) -> GatedLanguage | None:
        """The EN to store, or ``None`` when no English version was obtained."""
        wrong = portuguese_sections(check.en.sections)
        if not wrong:
            return check.en
        logger.warning(LOG_EN_WRONG_LANGUAGE, post_id=check.post_id, sections=wrong)
        for attempt in range(1, self._deps.max_retranslations + 1):
            sections = await self._retranslate(check, attempt)
            if sections is None:
                continue
            gated = await self._deps.gate.assess(
                GateCommand(LANGUAGE_EN, sections, check.brief)
            )
            return dataclasses.replace(gated, rewrite_passes=check.en.rewrite_passes)
        return None

    async def _retranslate(
        self, check: EnglishCheck, attempt: int
    ) -> tuple[DraftSection, ...] | None:
        """One retranslation of the gated PT; ``None`` if it failed / is not EN."""
        source = as_language_document(check.pt.sections)
        try:
            english = await self._deps.translator.translate(check.post_id, source)
        except BlogTranslationError as exc:
            logger.warning(LOG_EN_RETRANSLATION_FAILED, attempt=attempt, code=exc.code)
            return None
        sections = as_draft_sections(english)
        wrong = portuguese_sections(sections)
        if wrong:
            logger.warning(LOG_EN_RETRANSLATION_FAILED, attempt=attempt, sections=wrong)
            return None
        return sections


__all__ = [
    "EnglishCheck",
    "EnglishGateDeps",
    "EnglishLanguageGate",
    "as_draft_sections",
    "as_language_document",
]
