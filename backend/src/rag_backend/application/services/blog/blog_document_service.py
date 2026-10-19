"""The single owner of the blog document shape (AE-0423, ADR-0025).

``BlogDocumentService`` validates every write of ``blog_posts.content`` as
``blog.v2`` (strict: there is no v1 write path), keeps ``featured_image_url``
equal to ``content.cover.url`` (the column is a projection of the cover), and
guards publish. Reads go through :meth:`read_document`, which is strict too: a
non-v2 row raises :class:`InvalidBlogDocumentError` (fails closed with the
standard error/404) instead of adapting legacy markdown. The temporary AE-0423
read fail-safe was removed in AE-0428; that removal is gated on the owner
running ``python -m rag_backend.scripts.blog_v1_to_v2 --verify`` on production
(exit 0 = zero non-v2 rows, translations included) after AE-0423 is deployed,
because ``deploy.yml`` always brings the stack up even when the cutover fails.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.domain.constants.blog_document import (
    BLOG_HEADING_MARKER,
    BLOG_HEADING_MAX_CHARS,
    BLOG_SECTION_MAX_CHARS,
    ERR_BLOG_HEADING_INVALID,
    ERR_BLOG_NO_SECTIONS,
    ERR_BLOG_NOT_PUBLISHABLE,
    ERR_BLOG_SECTION_TOO_LONG,
    GENERATION_KEY,
    GENERATION_STATUS_IN_PROGRESS,
    GENERATION_STATUS_KEY,
)
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    BlogImage,
    BlogLanguageDocument,
    BlogSection,
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.models.blog_document_split import build_language_document


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
    def read_document(content: object) -> BlogDocument:
        """Parse a stored document for display; a non-v2 row fails closed.

        Raises :class:`InvalidBlogDocumentError` on anything that is not a valid
        ``blog.v2`` document (the caller maps it to the standard 422/404). There
        is no legacy-markdown adapter: after the cutover every row is v2.
        """
        return parse_blog_content(content)


__all__ = [
    "BlogDocumentService",
    "BlogDocumentWrite",
    "is_generation_in_progress",
]
