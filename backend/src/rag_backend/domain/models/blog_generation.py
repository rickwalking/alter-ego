"""Value objects of the blog writer + image run (AE-0425, ADR-0025).

The writer turns a :class:`WriterBrief` (raw material + one narrative role per
section + the persona) into a :class:`DraftArticle` (PT sections + the EN
translation). The quality gate scores and scans it, and the image step attaches
one image per slot. :class:`GenerationLease` identifies the run that may write
the row: every write is fenced on its ``lease_id``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from rag_backend.domain.models.blog_document import BlogDocument
from rag_backend.domain.models.persona import PersonaProfile


class LeaseLostError(RuntimeError):
    """The row's ``generation.lease_id`` is no longer this run's (a newer attempt)."""


class GenerationConflictError(RuntimeError):
    """The owner edited the row during the run (``lock_version`` moved)."""


class SectionCountMismatchError(ValueError):
    """The writer's sections cannot be normalized to the carousel slide count."""


class WriterFailedError(RuntimeError):
    """The writer produced no usable article (error, timeout, empty, bad JSON)."""


@dataclass(frozen=True)
class OutlinePoint:
    """One outline item of the source carousel (raw material, not text to copy)."""

    title: str
    key_points: tuple[str, ...] = ()


@dataclass(frozen=True)
class WriterBrief:
    """Everything the writer receives for one article.

    ``section_roles`` fixes the section count (one role per section, the
    carousel's slide count) and gives every section a distinct narrative job.
    """

    title: str
    topic: str
    section_roles: tuple[str, ...]
    persona: PersonaProfile
    research: tuple[str, ...] = ()
    outline: tuple[OutlinePoint, ...] = ()
    notes: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()

    @property
    def section_count(self) -> int:
        """How many sections the document must have (N)."""
        return len(self.section_roles)


@dataclass(frozen=True)
class DraftSection:
    """One written section: optional heading (``None`` for the lede) + markdown."""

    heading: str | None
    body_md: str


@dataclass(frozen=True)
class DraftArticle:
    """The writer's output: the canonical PT article and its EN translation."""

    title: str
    sections: tuple[DraftSection, ...]
    en_title: str
    en_sections: tuple[DraftSection, ...]


@dataclass(frozen=True)
class QualityFindings:
    """Deterministic scan result: repeated sentences and banned stock phrases."""

    repeated_sentences: tuple[str, ...] = ()
    banned_phrases: tuple[str, ...] = ()
    # Headings (or "#<index>") of PT sections that read as English (F-05).
    english_sections: tuple[str, ...] = ()

    @property
    def has_findings(self) -> bool:
        """True when the scan found anything that warrants the rewrite pass."""
        return bool(
            self.repeated_sentences or self.banned_phrases or self.english_sections
        )


@dataclass(frozen=True)
class VoiceScore:
    """``PersonaAgent.evaluate_match`` on 0-100: ``overall`` + the breakdown."""

    overall: float
    breakdown: dict[str, float | list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class RewriteRequest:
    """One rewrite pass over one language of the article."""

    language: str
    sections: tuple[DraftSection, ...]
    brief: WriterBrief
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class JudgeRequest:
    """What the reasoning model judges before the single rewrite pass."""

    language: str
    sections: tuple[DraftSection, ...]
    findings: QualityFindings
    voice: VoiceScore


@dataclass(frozen=True)
class GatedLanguage:
    """One language after the quality gate (sections + the stored quality)."""

    sections: tuple[DraftSection, ...]
    voice: VoiceScore
    findings: QualityFindings
    rewrite_passes: int


@dataclass(frozen=True)
class ImageSubject:
    """What one image depicts: the cover (title + lede) or a section."""

    slot: str
    heading: str
    body: str


@dataclass
class GenerationLease:
    """The run's write fence; ``lock_version`` follows the run's own writes."""

    post_id: str
    lease_id: str
    lock_version: int


@dataclass(frozen=True)
class GenerationTrace:
    """Langfuse metadata of the run (``project_id`` = carousel or the post)."""

    project_id: str
    user_id: str
    post_id: str


DocumentEdit = Callable[[BlogDocument], BlogDocument]


@dataclass(frozen=True)
class DocumentApply:
    """One content write of a run, applied onto the row's LATEST document.

    ``edit`` maps the latest document to the new one (it may raise, e.g.
    ``GenerationConflictError`` when the owner already wrote an article);
    ``images_generated`` is counted against the post's image cap;
    ``discard`` cleans up (new image files) when the write fails.
    """

    edit: DocumentEdit
    images_generated: int = 0
    voice_score: float | None = None
    discard: Callable[[], None] | None = None


@dataclass(frozen=True)
class GenerationOutcome:
    """The final, metadata-only write of a run (``title``: a standalone
    post takes the writer's title)."""

    status: str
    errors: tuple[dict[str, object], ...] = ()
    recoverable: bool = False
    image_count: int = 0
    title: str | None = None


__all__ = [
    "DocumentApply",
    "DocumentEdit",
    "DraftArticle",
    "DraftSection",
    "GatedLanguage",
    "GenerationConflictError",
    "GenerationLease",
    "GenerationOutcome",
    "GenerationTrace",
    "ImageSubject",
    "JudgeRequest",
    "LeaseLostError",
    "OutlinePoint",
    "QualityFindings",
    "RewriteRequest",
    "SectionCountMismatchError",
    "VoiceScore",
    "WriterBrief",
    "WriterFailedError",
]
