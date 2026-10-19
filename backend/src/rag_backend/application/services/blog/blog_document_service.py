"""The single owner of the blog document shape (AE-0423, ADR-0025).

``BlogDocumentService`` validates every write of ``blog_posts.content`` as
``blog.v2`` (strict: there is no v1 write path), keeps ``featured_image_url``
equal to ``content.cover.url`` (the column is a projection of the cover), and
guards publish. Reads go through :meth:`read_document`, which carries the
**temporary** fail-safe for a row the cutover has not reached yet: the legacy
markdown is adapted in memory to a text-only v2 document (never persisted,
never a carousel slide, never a 500) and ``blog_v2_non_migrated_rows`` is
emitted. AE-0428 deletes that adapter once prod ``--verify`` reports zero.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass

import structlog

from rag_backend.domain.constants.blog_document import (
    BLOG_HEADING_MARKER,
    BLOG_HEADING_MAX_CHARS,
    BLOG_SECTION_ID_PREFIX,
    BLOG_SECTION_MAX_CHARS,
    ERR_BLOG_HEADING_INVALID,
    ERR_BLOG_NO_SECTIONS,
    ERR_BLOG_NOT_PUBLISHABLE,
    ERR_BLOG_SECTION_TOO_LONG,
    GENERATION_KEY,
    GENERATION_STATUS_IN_PROGRESS,
    GENERATION_STATUS_KEY,
    METRIC_BLOG_V2_NON_MIGRATED_ROWS,
)
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    BlogImage,
    BlogLanguageDocument,
    BlogSection,
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.models.blog_document_split import (
    SectionIdFactory,
    build_language_document,
    migrate_content,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BlogDocumentWrite:
    """A validated document plus the column projection written with it."""

    content: dict[str, object]
    featured_image_url: str | None


def is_generation_in_progress(metadata: object) -> bool:
    """``ai_generation_metadata.generation.status == "in_progress"``."""
    if not isinstance(metadata, dict):
        return False
    generation = metadata.get(GENERATION_KEY)
    if not isinstance(generation, dict):
        return False
    return generation.get(GENERATION_STATUS_KEY) == GENERATION_STATUS_IN_PROGRESS


def _check_heading(heading: str | None) -> None:
    if heading is None:
        return
    stripped = heading.strip()
    if not stripped or stripped.startswith(BLOG_HEADING_MARKER):
        raise InvalidBlogDocumentError(ERR_BLOG_HEADING_INVALID)
    if len(heading) > BLOG_HEADING_MAX_CHARS:
        raise InvalidBlogDocumentError(ERR_BLOG_HEADING_INVALID)


def _check_section(section: BlogSection) -> None:
    _check_heading(section.heading)
    if len(section.body_md) > BLOG_SECTION_MAX_CHARS:
        raise InvalidBlogDocumentError(ERR_BLOG_SECTION_TOO_LONG, section.id)


def _check_language(document: BlogLanguageDocument, *, allow_empty: bool) -> None:
    if not document.sections and not allow_empty:
        raise InvalidBlogDocumentError(ERR_BLOG_NO_SECTIONS)
    for section in document.sections:
        _check_section(section)


def _has_body(document: BlogLanguageDocument) -> bool:
    return any(section.body_md.strip() for section in document.sections)


class BlogDocumentService:
    """Validate, project and safely read ``blog.v2`` documents."""

    @staticmethod
    def initial_content() -> dict[str, object]:
        """A fresh, valid document: one empty lede section, no cover."""
        return parse_blog_content(build_language_document("")).to_content()

    @staticmethod
    def validate_for_write(
        content: object, *, generation_in_progress: bool = False
    ) -> BlogDocumentWrite:
        """Strict write validation; raises :class:`InvalidBlogDocumentError`.

        Zero sections are allowed only while generation is in progress.
        """
        document = parse_blog_content(content)
        _check_language(document, allow_empty=generation_in_progress)
        for translation in document.translations.values():
            _check_language(translation, allow_empty=generation_in_progress)
        cover_url = document.cover.url if document.cover else None
        return BlogDocumentWrite(document.to_content(), cover_url)

    @staticmethod
    def with_cover(content: object, cover: BlogImage | None) -> BlogDocumentWrite:
        """Replace (or clear) the PT cover and re-project ``featured_image_url``."""
        document = parse_blog_content(content)
        updated = document.model_copy(update={"cover": cover})
        return BlogDocumentService.validate_for_write(updated.to_content())

    @staticmethod
    def assert_publishable(content: object) -> None:
        """Publish needs a valid v2 document with >= 1 non-empty section."""
        try:
            document = parse_blog_content(content)
        except InvalidBlogDocumentError as exc:
            raise InvalidBlogDocumentError(ERR_BLOG_NOT_PUBLISHABLE, exc.code) from exc
        if not _has_body(document):
            raise InvalidBlogDocumentError(ERR_BLOG_NOT_PUBLISHABLE)

    @staticmethod
    def read_document(content: object, post_id: str) -> BlogDocument:
        """Parse for display; adapt a non-migrated legacy row (temporary)."""
        try:
            return parse_blog_content(content)
        except InvalidBlogDocumentError as exc:
            logger.warning(
                METRIC_BLOG_V2_NON_MIGRATED_ROWS, post_id=post_id, reason=exc.code
            )
            return _adapt_in_memory(content, post_id)


def _stable_section_ids(post_id: str) -> SectionIdFactory:
    """Deterministic ids so repeated reads of one legacy row are identical."""
    counter = itertools.count()

    def _next_id() -> str:
        seed = f"{post_id}:{next(counter)}"
        return f"{BLOG_SECTION_ID_PREFIX}{uuid.uuid5(uuid.NAMESPACE_URL, seed)}"

    return _next_id


def _adapt_in_memory(content: object, post_id: str) -> BlogDocument:
    new_id = _stable_section_ids(post_id)
    try:
        return parse_blog_content(migrate_content(content, new_id))
    except InvalidBlogDocumentError:
        return parse_blog_content(build_language_document("", new_id))


__all__ = [
    "BlogDocumentService",
    "BlogDocumentWrite",
    "is_generation_in_progress",
]
