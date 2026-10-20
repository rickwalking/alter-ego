"""Ports of the blog writer + image run (AE-0425, ADR-0025).

The application service orchestrates the run through these ports only: the
writer agent (``agents/blog_writer``) implements :class:`BlogArticleWriter`,
:class:`VoiceScorer`; the database adapter
implements :class:`BlogGenerationStore` (lease-fenced writes) and
:class:`BlogGenerationReaper` (the worker-tick step).
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models.blog_document import BlogLanguageDocument
from rag_backend.domain.models.blog_generation import (
    DocumentApply,
    DraftArticle,
    DraftSection,
    GenerationLease,
    GenerationOutcome,
    JudgeRequest,
    RewriteRequest,
    VoiceScore,
    WriterBrief,
)


class BlogArticleWriter(Protocol):
    """Writes ONE continuous article in the persona's voice (PT + EN)."""

    async def draft(self, brief: WriterBrief) -> DraftArticle:
        """Draft the article; ``WriterFailedError`` when nothing usable came back."""
        ...

    async def rewrite(self, request: RewriteRequest) -> tuple[DraftSection, ...]:
        """The single rewrite pass of one language."""
        ...

    async def judge(self, request: JudgeRequest) -> tuple[str, ...]:
        """Reasoning-model revision notes for the rewrite pass (may be empty)."""
        ...


class BlogDocumentTranslator(Protocol):
    """PT -> EN translation of a language document (AE-0424's
    ``BlogTranslationService``; AE-0435 reuses it to repair a wrong-language EN)."""

    async def translate(
        self, post_id: str, source: BlogLanguageDocument
    ) -> BlogLanguageDocument:
        """The EN document; raises ``BlogTranslationError`` on any failure."""
        ...


class VoiceScorer(Protocol):
    """Scores text against the persona (``PersonaAgent.evaluate_match``)."""

    async def score(self, text: str) -> VoiceScore:
        """The 0-100 voice score of ``text``."""
        ...


class BlogGenerationStore(Protocol):
    """Lease-fenced writes of one run (``WHERE lease_id = :mine``)."""

    async def heartbeat(self, lease: GenerationLease) -> None:
        """Stamp ``generation.heartbeat_at``; raises ``LeaseLostError``."""
        ...

    async def read_content(self, lease: GenerationLease) -> dict[str, object]:
        """The row's current ``content``; raises ``LeaseLostError``."""
        ...

    async def reserve_images(self, lease: GenerationLease, wanted: int) -> int:
        """Reserve up to ``wanted`` images of the post's cap BEFORE the spend
        (under the row lock); returns how many were granted."""
        ...

    async def apply_document(
        self, lease: GenerationLease, change: DocumentApply
    ) -> None:
        """Lock the row, apply ``change.edit`` onto its LATEST document and store
        it (an owner save made meanwhile is the base, never a conflict)."""
        ...

    async def finish(self, lease: GenerationLease, outcome: GenerationOutcome) -> None:
        """Record the final status/errors (metadata only); raises ``LeaseLostError``."""
        ...


class BlogGenerationReaper(Protocol):
    """Worker-tick step: fails runs whose heartbeat went stale (restart/kill)."""

    async def tick(self, db: AsyncSession) -> int:
        """Reap stale ``in_progress`` rows; returns how many were reaped."""
        ...


__all__ = [
    "BlogArticleWriter",
    "BlogDocumentTranslator",
    "BlogGenerationReaper",
    "BlogGenerationStore",
    "VoiceScorer",
]
