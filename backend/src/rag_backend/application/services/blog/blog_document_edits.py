"""Targeted edits of one slot of a ``blog.v2`` document (AE-0424).

The image, rewrite and translation routes change exactly one thing — a cover,
a section image, a section body or the EN translation — of the language the
editor is showing (PT is the top level, EN is ``translations.en``). These pure
helpers return a new document with only that slot replaced; the other language
and every other section stay byte-identical. The result is re-validated by
``BlogDocumentService.validate_for_write`` before it is stored.
"""

from __future__ import annotations

from rag_backend.domain.constants.blog_editor import (
    BLOG_LANGUAGE_EN,
    BLOG_LANGUAGE_PT,
    ERR_BLOG_SECTION_NOT_FOUND,
    ERR_BLOG_TRANSLATION_MISSING,
)
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    BlogImage,
    BlogLanguageDocument,
    BlogSection,
)


class BlogEditError(LookupError):
    """The addressed language/section does not exist; ``code`` is the detail."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def language_document(document: BlogDocument, language: str) -> BlogLanguageDocument:
    """The PT document itself, or its translation (missing -> error)."""
    if language == BLOG_LANGUAGE_PT:
        return document
    translation = document.translations.get(language)
    if translation is None:
        raise BlogEditError(ERR_BLOG_TRANSLATION_MISSING)
    return translation


def find_section(document: BlogLanguageDocument, section_id: str) -> BlogSection:
    """The section with ``section_id``; raises :class:`BlogEditError` if absent."""
    for section in document.sections:
        if section.id == section_id:
            return section
    raise BlogEditError(ERR_BLOG_SECTION_NOT_FOUND)


def _replace_language(
    document: BlogDocument, language: str, updated: BlogLanguageDocument
) -> BlogDocument:
    if language == BLOG_LANGUAGE_PT:
        return document.model_copy(
            update={"cover": updated.cover, "sections": updated.sections}
        )
    translations = {**document.translations, language: updated}
    return document.model_copy(update={"translations": translations})


def with_section(
    document: BlogDocument, language: str, section: BlogSection
) -> BlogDocument:
    """Replace the section that has ``section.id`` (its position is kept)."""
    current = language_document(document, language)
    find_section(current, section.id)
    sections = [section if s.id == section.id else s for s in current.sections]
    updated = current.model_copy(update={"sections": sections})
    return _replace_language(document, language, updated)


def with_cover(
    document: BlogDocument, language: str, cover: BlogImage | None
) -> BlogDocument:
    """Set (or clear) the cover of one language."""
    current = language_document(document, language)
    updated = current.model_copy(update={"cover": cover})
    return _replace_language(document, language, updated)


def with_translation(
    document: BlogDocument, translation: BlogLanguageDocument
) -> BlogDocument:
    """Store ``translation`` as ``translations.en`` (PT untouched)."""
    return _replace_language(document, BLOG_LANGUAGE_EN, translation)


__all__ = [
    "BlogEditError",
    "find_section",
    "language_document",
    "with_cover",
    "with_section",
    "with_translation",
]
