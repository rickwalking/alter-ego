"""Assemble the ``blog.v2`` document of a generated post (ADR-0025).

PT is canonical (``sections``); EN lives in ``translations.en`` with the **same
section ids**, so a section's image and its translation stay attached through
reorders. Each language stores its own ``quality``. Images are attached per
slot afterwards onto the CURRENT row content (:func:`attach_images`, only empty
slots, so owner edits made meanwhile survive); EN reuses the PT image file with its
own alt text.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from rag_backend.domain.constants.blog_document import BLOG_SCHEMA_V2, KEY_SCHEMA
from rag_backend.domain.constants.blog_generation import (
    IMAGE_SLOT_COVER,
    LANGUAGE_EN,
)
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    BlogImage,
    BlogLanguageDocument,
    BlogQuality,
    BlogRepetition,
    BlogSection,
)
from rag_backend.domain.models.blog_generation import GatedLanguage, ImageSubject


@dataclass(frozen=True)
class ImageTitles:
    """The PT and EN titles (cover subject + cover alt per language)."""

    title: str
    en_title: str


@dataclass(frozen=True)
class GeneratedLanguages:
    """Both gated languages plus the titles used for cover subjects/alt.

    ``en`` is ``None`` when the EN gate could not obtain English:
    the document is then stored without ``translations.en``.
    """

    pt: GatedLanguage
    en: GatedLanguage | None
    title: str
    en_title: str


def _new_section_id() -> str:
    return f"sec_{uuid.uuid4()}"


def _quality(gated: GatedLanguage, checked_at: str) -> BlogQuality:
    return BlogQuality(
        voice_score=max(0.0, min(100.0, gated.voice.overall)),
        voice_breakdown=dict(gated.voice.breakdown),
        repetition=BlogRepetition(
            repeated_sentences=list(gated.findings.repeated_sentences),
            banned_phrases=list(gated.findings.banned_phrases),
        ),
        rewrite_passes=gated.rewrite_passes,
        checked_at=checked_at,
    )


def _sections(gated: GatedLanguage, ids: list[str]) -> list[BlogSection]:
    return [
        BlogSection(id=section_id, heading=section.heading, body_md=section.body_md)
        for section_id, section in zip(ids, gated.sections, strict=True)
    ]


def _language(
    gated: GatedLanguage, ids: list[str], checked_at: str
) -> BlogLanguageDocument:
    return BlogLanguageDocument.model_validate({
        KEY_SCHEMA: BLOG_SCHEMA_V2,
        "sections": _sections(gated, ids),
        "quality": _quality(gated, checked_at),
    })


def build_generated_document(
    languages: GeneratedLanguages, checked_at: str
) -> BlogDocument:
    """The image-less document (PT + EN, scored) with fresh shared section ids."""
    ids = [_new_section_id() for _ in languages.pt.sections]
    translations = (
        {}
        if languages.en is None
        else {LANGUAGE_EN: _language(languages.en, ids, checked_at)}
    )
    return BlogDocument.model_validate({
        KEY_SCHEMA: BLOG_SCHEMA_V2,
        "sections": _sections(languages.pt, ids),
        "translations": translations,
        "quality": _quality(languages.pt, checked_at),
    })


def missing_image_subjects(
    document: BlogDocument, title: str
) -> tuple[ImageSubject, ...]:
    """The PT slots still without an image: cover (title + lede) first, then
    each section in order. A fresh document has N + 1; a retry only the gaps."""
    lede = document.sections[0].body_md if document.sections else ""
    cover = (
        (ImageSubject(slot=IMAGE_SLOT_COVER, heading=title, body=lede),)
        if document.cover is None
        else ()
    )
    sections = tuple(
        ImageSubject(
            slot=section.id, heading=section.heading or title, body=section.body_md
        )
        for section in document.sections
        if section.image is None
    )
    return (*cover, *sections)


def _with_alt(image: BlogImage, alt: str) -> BlogImage:
    return image.model_copy(update={"alt": alt})


def _fill_language(
    language: BlogLanguageDocument, images: dict[str, BlogImage], cover_alt: str
) -> dict[str, object]:
    """Fill only EMPTY slots; an image the owner set meanwhile is kept, and a
    section the owner deleted meanwhile simply no longer matches."""
    cover = language.cover
    if cover is None and IMAGE_SLOT_COVER in images:
        cover = _with_alt(images[IMAGE_SLOT_COVER], cover_alt)
    sections = [
        section.model_copy(
            update={
                "image": _with_alt(images[section.id], section.heading or cover_alt)
            }
        )
        if section.image is None and section.id in images
        else section
        for section in language.sections
    ]
    return {"cover": cover, "sections": sections}


def attach_images(
    document: BlogDocument, images: dict[str, BlogImage], titles: ImageTitles
) -> BlogDocument:
    """Attach generated images by slot id to the CURRENT document (PT + each
    translation, which shares the PT section ids)."""
    translations = {
        language: translation.model_copy(
            update=_fill_language(translation, images, titles.en_title)
        )
        for language, translation in document.translations.items()
    }
    pt = _fill_language(document, images, titles.title)
    return document.model_copy(update={**pt, "translations": translations})


def placed_slots(document: BlogDocument, images: dict[str, BlogImage]) -> set[str]:
    """The slots whose generated image is in ``document`` (PT) after attaching."""
    urls = {image.url: slot for slot, image in images.items()}
    found = [document.cover, *(section.image for section in document.sections)]
    return {
        urls[image.url] for image in found if image is not None and image.url in urls
    }


__all__ = [
    "GeneratedLanguages",
    "ImageTitles",
    "attach_images",
    "build_generated_document",
    "missing_image_subjects",
    "placed_slots",
]
