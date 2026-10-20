"""The blocking quality gate of a generated article (AE-0425, ADR-0025).

Per language (PT canonical, then ``translations.en``):

1. PT only: research sentences copied verbatim are stripped (F-05 class).
2. ``VoiceScorer.score`` (``PersonaAgent.evaluate_match``) + the deterministic
   scan (repetition, verbatim note copies, banned stock phrases).
3. ``overall < 70`` or any finding → the reasoning model judges what to fix and
   the writer performs **exactly one** rewrite pass, then the article is
   re-normalized, re-stripped and re-scored. The second score is stored as is:
   there is never a second rewrite.
4. EN only (AE-0435): a rewrite that switched the article to Portuguese is
   discarded and the English sections from before it are kept (the PT persona
   scorer's Portuguese suggestions used to pull the EN rewrite into Portuguese).
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.application.services.blog.blog_quality_scan import (
    ScanInput,
    portuguese_sections,
    scan_sections,
    strip_source_leaks,
)
from rag_backend.application.services.blog.blog_section_plan import (
    normalize_section_count,
)
from rag_backend.domain.constants.blog_generation import (
    LANGUAGE_EN,
    LANGUAGE_PT,
    LOG_EN_REWRITE_DISCARDED,
    LOG_SOURCE_LEAK_STRIPPED,
)
from rag_backend.domain.constants.blog_voice import (
    MAX_REWRITE_PASSES,
    VOICE_SCORE_THRESHOLD,
)
from rag_backend.domain.models.blog_generation import (
    DraftSection,
    GatedLanguage,
    JudgeRequest,
    QualityFindings,
    RewriteRequest,
    VoiceScore,
    WriterBrief,
)
from rag_backend.domain.protocols.blog_generation import BlogArticleWriter, VoiceScorer

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class QualityGateDeps:
    """The writer (rewrite + judge) and the persona voice scorer."""

    writer: BlogArticleWriter
    scorer: VoiceScorer


@dataclass(frozen=True)
class GateCommand:
    """One language of the article to gate."""

    language: str
    sections: tuple[DraftSection, ...]
    brief: WriterBrief


@dataclass(frozen=True)
class _Assessment:
    sections: tuple[DraftSection, ...]
    voice: VoiceScore
    findings: QualityFindings

    @property
    def passed(self) -> bool:
        return self.voice.overall >= VOICE_SCORE_THRESHOLD and not (
            self.findings.has_findings
        )


def article_text(sections: tuple[DraftSection, ...]) -> str:
    """The article as one text (headings + bodies) for the voice scorer."""
    parts = [
        f"{section.heading}\n\n{section.body_md}"
        if section.heading
        else section.body_md
        for section in sections
    ]
    return "\n\n".join(part.strip() for part in parts if part.strip())


class BlogQualityGate:
    """Voice score + deterministic scan + at most one rewrite pass."""

    def __init__(self, deps: QualityGateDeps) -> None:
        self._deps = deps

    async def run(self, command: GateCommand) -> GatedLanguage:
        """Gate one language; the result carries the stored quality inputs."""
        first = await self._assess(command, command.sections)
        if first.passed:
            return GatedLanguage(first.sections, first.voice, first.findings, 0)
        rewritten = await self._rewrite(command, first)
        if _switched_to_portuguese(command.language, first, rewritten):
            logger.warning(LOG_EN_REWRITE_DISCARDED)
            return GatedLanguage(
                first.sections, first.voice, first.findings, MAX_REWRITE_PASSES
            )
        second = await self._assess(command, rewritten)
        return GatedLanguage(
            second.sections, second.voice, second.findings, MAX_REWRITE_PASSES
        )

    async def _rewrite(
        self, command: GateCommand, first: _Assessment
    ) -> tuple[DraftSection, ...]:
        """The judge's notes → the single rewrite pass, re-normalized."""
        notes = await self._deps.writer.judge(
            JudgeRequest(
                language=command.language,
                sections=first.sections,
                findings=first.findings,
                voice=first.voice,
            )
        )
        rewritten = await self._deps.writer.rewrite(
            RewriteRequest(
                language=command.language,
                sections=first.sections,
                brief=command.brief,
                notes=notes,
            )
        )
        return normalize_section_count(rewritten, command.brief.section_count)

    async def assess(self, command: GateCommand) -> GatedLanguage:
        """Score + scan ``command.sections`` without any rewrite (AE-0435: a
        retranslated EN is stored with its own quality)."""
        assessed = await self._assess(command, command.sections)
        return GatedLanguage(assessed.sections, assessed.voice, assessed.findings, 0)

    async def _assess(
        self, command: GateCommand, sections: tuple[DraftSection, ...]
    ) -> _Assessment:
        cleaned = self._without_leaks(command, sections)
        voice = await self._deps.scorer.score(article_text(cleaned))
        notes = command.brief.notes if command.language == LANGUAGE_PT else ()
        findings = scan_sections(
            ScanInput(language=command.language, sections=cleaned, notes=notes)
        )
        return _Assessment(cleaned, voice, findings)

    @staticmethod
    def _without_leaks(
        command: GateCommand, sections: tuple[DraftSection, ...]
    ) -> tuple[DraftSection, ...]:
        if command.language != LANGUAGE_PT:
            return sections
        cleaned, dropped = strip_source_leaks(sections, command.brief.research)
        if dropped:
            logger.warning(LOG_SOURCE_LEAK_STRIPPED, sentences=dropped)
        return cleaned


def _switched_to_portuguese(
    language: str, before: _Assessment, after: tuple[DraftSection, ...]
) -> bool:
    """An EN rewrite that reads as Portuguese where the draft read as English."""
    if language != LANGUAGE_EN:
        return False
    return bool(portuguese_sections(after)) and not portuguese_sections(before.sections)


__all__ = ["BlogQualityGate", "GateCommand", "QualityGateDeps", "article_text"]
