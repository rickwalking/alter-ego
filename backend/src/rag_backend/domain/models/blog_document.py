"""The blog post document model (``blog.v2``, AE-0423, ADR-0025).

``blog_posts.content`` holds exactly one shape: a versioned, section-structured
document with a cover, ordered sections (stable ids, own image) and per-language
translations. :func:`parse_blog_content` is strict: it returns a
:class:`BlogDocument` or raises :class:`InvalidBlogDocumentError`; it never
coerces a legacy markdown string into a section (the one-shot cutover is the
only bridge from the old shape).

These are the *structural* rules shared by every read and write. Write-only
rules (section length, heading form, non-empty document) live in
``BlogDocumentService`` so a migrated row with an oversized section still reads.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from rag_backend.domain.constants.blog_document import (
    BLOG_HTTPS_SCHEME_PREFIX,
    BLOG_LANGUAGE_PATTERN,
    BLOG_PROTOCOL_RELATIVE_PREFIX,
    BLOG_SAME_ORIGIN_PATH_PREFIX,
    BLOG_SCHEMA_V2,
    BLOG_SECTION_ID_PATTERN,
    ERR_BLOG_DOCUMENT_NOT_OBJECT,
    ERR_BLOG_DOCUMENT_NOT_V2,
    ERR_BLOG_DUPLICATE_SECTION_ID,
    ERR_BLOG_IMAGE_ALT_BLANK,
    ERR_BLOG_IMAGE_URL_INVALID,
    ERR_BLOG_TRANSLATION_LANGUAGE_INVALID,
    ERR_INVALID_BLOG_DOCUMENT,
    KEY_SCHEMA,
)

_FORBID_EXTRA = ConfigDict(extra="forbid", frozen=True)

ImageSource = Literal["generated", "upload"]


class InvalidBlogDocumentError(ValueError):
    """``content`` is not a valid ``blog.v2`` document; ``code`` is the API detail."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def _is_allowed_image_url(url: str) -> bool:
    if url.startswith(BLOG_HTTPS_SCHEME_PREFIX):
        return True
    if url.startswith(BLOG_PROTOCOL_RELATIVE_PREFIX):
        return False
    return url.startswith(BLOG_SAME_ORIGIN_PATH_PREFIX)


class BlogImage(BaseModel):
    """A cover or section image; ``alt`` is mandatory and never blank."""

    model_config = _FORBID_EXTRA

    url: str = Field(min_length=1)
    alt: str = Field(min_length=1)
    caption: str | None = None
    source: ImageSource = "generated"
    prompt: str | None = None
    model: str | None = None
    created_at: str | None = None

    @field_validator("alt")
    @classmethod
    def _alt_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(ERR_BLOG_IMAGE_ALT_BLANK)
        return value

    @field_validator("url")
    @classmethod
    def _url_allowed(cls, value: str) -> str:
        if not _is_allowed_image_url(value):
            raise ValueError(ERR_BLOG_IMAGE_URL_INVALID)
        return value


class BlogSection(BaseModel):
    """One ordered section; ``id`` is stable across reorder/rename."""

    model_config = _FORBID_EXTRA

    id: str = Field(pattern=BLOG_SECTION_ID_PATTERN)
    heading: str | None = None
    body_md: str = ""
    image: BlogImage | None = None


class BlogRepetition(BaseModel):
    """Repetition findings of the quality gate (AE-0425 writes them)."""

    model_config = _FORBID_EXTRA

    repeated_sentences: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)


class BlogQuality(BaseModel):
    """Voice/repetition scores; editor-only (never in the public payload)."""

    model_config = _FORBID_EXTRA

    voice_score: float = Field(ge=0, le=100)
    voice_breakdown: dict[str, float | list[str]] = Field(default_factory=dict)
    repetition: BlogRepetition = Field(default_factory=BlogRepetition)
    rewrite_passes: int = Field(default=0, ge=0)
    checked_at: str | None = None


def _require_unique_ids(sections: list[BlogSection]) -> list[BlogSection]:
    ids = [section.id for section in sections]
    if len(ids) != len(set(ids)):
        raise ValueError(ERR_BLOG_DUPLICATE_SECTION_ID)
    return sections


class BlogLanguageDocument(BaseModel):
    """One language of the document (PT top level, or a translation)."""

    model_config = _FORBID_EXTRA

    schema_: Literal["blog.v2"] = Field(alias=KEY_SCHEMA)
    cover: BlogImage | None = None
    sections: list[BlogSection] = Field(default_factory=list)
    quality: BlogQuality | None = None

    @field_validator("sections")
    @classmethod
    def _unique_section_ids(cls, value: list[BlogSection]) -> list[BlogSection]:
        return _require_unique_ids(value)


class BlogDocument(BlogLanguageDocument):
    """The canonical (PT) document plus its translations keyed by language."""

    translations: dict[str, BlogLanguageDocument] = Field(default_factory=dict)

    @field_validator("translations")
    @classmethod
    def _language_keys(
        cls, value: dict[str, BlogLanguageDocument]
    ) -> dict[str, BlogLanguageDocument]:
        for language in value:
            if re.fullmatch(BLOG_LANGUAGE_PATTERN, language) is None:
                raise ValueError(ERR_BLOG_TRANSLATION_LANGUAGE_INVALID)
        return value

    def to_content(self) -> dict[str, object]:
        """Serialize to the persisted JSON shape (``schema`` key restored)."""
        return self.model_dump(mode="json", by_alias=True)


def _describe(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"{location}: {first['msg']}" if location else str(first["msg"])


def parse_blog_content(content: object) -> BlogDocument:
    """Validate ``content`` as ``blog.v2`` or raise :class:`InvalidBlogDocumentError`.

    Never coerces: a legacy string/markdown object, a JSON array, ``None`` or a
    document with any other ``schema`` value is rejected.
    """
    if not isinstance(content, dict):
        raise InvalidBlogDocumentError(ERR_BLOG_DOCUMENT_NOT_OBJECT)
    if content.get(KEY_SCHEMA) != BLOG_SCHEMA_V2:
        raise InvalidBlogDocumentError(ERR_BLOG_DOCUMENT_NOT_V2)
    try:
        return BlogDocument.model_validate(content)
    except ValidationError as exc:
        raise InvalidBlogDocumentError(
            ERR_INVALID_BLOG_DOCUMENT, _describe(exc)
        ) from exc


__all__ = [
    "BlogDocument",
    "BlogImage",
    "BlogLanguageDocument",
    "BlogQuality",
    "BlogRepetition",
    "BlogSection",
    "InvalidBlogDocumentError",
    "parse_blog_content",
]
