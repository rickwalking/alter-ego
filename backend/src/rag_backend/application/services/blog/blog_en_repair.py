"""Find and repair stored posts whose ``translations.en`` reads as Portuguese (AE-0435).

Before the EN language gate, generation could store Portuguese as English (prod
posts ba37f6f9 and 99886e71). This one-shot operator service:

* :meth:`BlogEnRepairService.scan` — read-only: every ``blog.v2`` post whose EN
  sections read as Portuguese (the same deterministic detector as the gate);
* :meth:`BlogEnRepairService.repair` — for the named posts only: translate the
  PT document with the editor's PT -> EN translation (which refuses a
  Portuguese answer) and replace ``translations.en``. The PT sections, the
  images and the cover are untouched; EN shares the PT section ids. A post whose
  EN already reads as English is skipped (nothing is written).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from rag_backend.application.services.blog.blog_english_gate import (
    as_draft_sections,
)
from rag_backend.application.services.blog.blog_quality_scan import (
    portuguese_sections,
)
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationError,
)
from rag_backend.domain.constants.blog_generation import LANGUAGE_EN
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    BlogLanguageDocument,
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.protocols.blog_generation import BlogDocumentTranslator

SKIP_NOT_FOUND = "not_found"
SKIP_NOT_V2 = "not_blog_v2"
SKIP_NO_EN = "no_en_translation"
SKIP_EN_OK = "en_reads_as_english"


@dataclass(frozen=True)
class StoredPost:
    """The fields of a stored post the repair reads."""

    post_id: str
    title: str
    content: object


class EnRepairStore(Protocol):
    """Read the posts; replace the EN of one post (versioned write)."""

    async def posts(self) -> list[StoredPost]:
        """Every blog post (id, title, content)."""
        ...

    async def post(self, post_id: str) -> StoredPost | None:
        """One post, ``None`` when it does not exist."""
        ...

    async def replace_english(
        self, post_id: str, english: BlogLanguageDocument
    ) -> None:
        """Store ``english`` as ``translations.en`` of the LATEST content."""
        ...


@dataclass(frozen=True)
class EnRepairDeps:
    """The posts store and the PT -> EN translator."""

    store: EnRepairStore
    translator: BlogDocumentTranslator


@dataclass(frozen=True)
class WrongEnglish:
    """A post whose EN sections read as Portuguese."""

    post_id: str
    title: str
    sections: tuple[str, ...]


@dataclass
class EnRepairReport:
    """What a scan found / what a repair did, per post."""

    wrong: list[WrongEnglish] = field(default_factory=list)
    repaired: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


def _document(content: object) -> BlogDocument | None:
    try:
        return parse_blog_content(content)
    except InvalidBlogDocumentError:
        return None


def wrong_english_sections(document: BlogDocument) -> tuple[str, ...] | None:
    """The EN sections that read as Portuguese; ``None`` when there is no EN."""
    english = document.translations.get(LANGUAGE_EN)
    if english is None:
        return None
    return portuguese_sections(as_draft_sections(english))


def english_like_pt(
    pt: BlogDocument, translated: BlogLanguageDocument
) -> BlogLanguageDocument:
    """``translated`` with the PT section ids, section images and cover."""
    sections = [
        section.model_copy(update={"id": source.id, "image": source.image})
        for source, section in zip(pt.sections, translated.sections, strict=True)
    ]
    return translated.model_copy(
        update={"sections": sections, "cover": pt.cover, "quality": None}
    )


def _skip_reason(document: BlogDocument | None) -> str | None:
    if document is None:
        return SKIP_NOT_V2
    wrong = wrong_english_sections(document)
    if wrong is None:
        return SKIP_NO_EN
    return None if wrong else SKIP_EN_OK


class BlogEnRepairService:
    """Scan (read-only) or repair the named posts (see the module docstring)."""

    def __init__(self, deps: EnRepairDeps) -> None:
        self._deps = deps

    async def scan(self) -> EnRepairReport:
        """Every post whose EN reads as Portuguese; nothing is written."""
        report = EnRepairReport()
        for post in await self._deps.store.posts():
            document = _document(post.content)
            wrong = wrong_english_sections(document) if document else None
            if wrong:
                report.wrong.append(WrongEnglish(post.post_id, post.title, wrong))
        return report

    async def repair(self, only: tuple[str, ...]) -> EnRepairReport:
        """Replace the Portuguese EN of each named post with a translation."""
        report = EnRepairReport()
        for post_id in only:
            await self._repair_one(post_id, report)
        return report

    async def _repair_one(self, post_id: str, report: EnRepairReport) -> None:
        post = await self._deps.store.post(post_id)
        document = _document(post.content) if post else None
        reason = SKIP_NOT_FOUND if post is None else _skip_reason(document)
        if reason is not None or document is None:
            report.skipped.append((post_id, reason or SKIP_NOT_V2))
            return
        try:
            translated = await self._deps.translator.translate(post_id, document)
        except BlogTranslationError as exc:
            report.failed.append((post_id, exc.code))
            return
        await self._deps.store.replace_english(
            post_id, english_like_pt(document, translated)
        )
        report.repaired.append(post_id)


__all__ = [
    "BlogEnRepairService",
    "EnRepairDeps",
    "EnRepairReport",
    "EnRepairStore",
    "StoredPost",
    "WrongEnglish",
    "english_like_pt",
    "wrong_english_sections",
]
