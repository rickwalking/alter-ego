"""The blocking quality gate of a generated article (AE-0425, ADR-0025).

Per language (PT canonical, then ``translations.en``):

1. PT only: research sentences copied verbatim are stripped (F-05 class).
2. ``VoiceScorer.score`` (``PersonaAgent.evaluate_match``) + the deterministic
   scan (repetition, verbatim note copies, banned stock phrases).
3. ``overall < 70`` or any finding → the reasoning model judges what to fix and
   the writer performs **exactly one** rewrite pass, then the article is
   re-normalized, re-stripped and re-scored. The second score is stored as is:
   there is never a second rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.application.services.blog.blog_quality_scan import (
    ScanInput,
    scan_sections,
    strip_source_leaks,
)
from rag_backend.application.services.blog.blog_section_plan import (
    normalize_section_count,
)
from rag_backend.domain.constants.blog_generation import (
    LANGUAGE_PT,
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
        normalized = normalize_section_count(rewritten, command.brief.section_count)
        second = await self._assess(command, normalized)
        return GatedLanguage(
            second.sections, second.voice, second.findings, MAX_REWRITE_PASSES
        )

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


__all__ = ["BlogQualityGate", "GateCommand", "QualityGateDeps", "article_text"]
