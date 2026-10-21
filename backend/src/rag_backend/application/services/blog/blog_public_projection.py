"""Public projection of a ``blog.v2`` document (ADR-0013, ADR-0025).

The public lean read serializes an explicit allow-list of the document:
``schema``, ``cover{url,alt,caption,source,created_at}``,
``sections[{id,heading,body_md,image{...}}]`` and the same per translation.
``quality``, ``image.prompt``, ``image.model`` and any generation metadata are
editor-only and never leave this function.
"""

from __future__ import annotations

from rag_backend.domain.constants.blog_document import (
    BLOG_SCHEMA_V2,
    KEY_ALT,
    KEY_BODY_MD,
    KEY_CAPTION,
    KEY_COVER,
    KEY_CREATED_AT,
    KEY_HEADING,
    KEY_ID,
    KEY_IMAGE,
    KEY_SCHEMA,
    KEY_SECTIONS,
    KEY_SOURCE,
    KEY_TRANSLATIONS,
    KEY_URL,
)
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    BlogImage,
    BlogLanguageDocument,
    BlogSection,
)


def _public_image(image: BlogImage | None) -> dict[str, object] | None:
    if image is None:
        return None
    return {
        KEY_URL: image.url,
        KEY_ALT: image.alt,
        KEY_CAPTION: image.caption,
        KEY_SOURCE: image.source,
        KEY_CREATED_AT: image.created_at,
    }


def _public_section(section: BlogSection) -> dict[str, object]:
    return {
        KEY_ID: section.id,
        KEY_HEADING: section.heading,
        KEY_BODY_MD: section.body_md,
        KEY_IMAGE: _public_image(section.image),
    }


def _public_language(document: BlogLanguageDocument) -> dict[str, object]:
    return {
        KEY_SCHEMA: BLOG_SCHEMA_V2,
        KEY_COVER: _public_image(document.cover),
        KEY_SECTIONS: [_public_section(section) for section in document.sections],
    }


def project_public_document(document: BlogDocument) -> dict[str, object]:
    """The public-safe ``content`` payload (allow-list, no editor-only fields)."""
    projected = _public_language(document)
    projected[KEY_TRANSLATIONS] = {
        language: _public_language(translation)
        for language, translation in document.translations.items()
    }
    return projected


__all__ = ["project_public_document"]
