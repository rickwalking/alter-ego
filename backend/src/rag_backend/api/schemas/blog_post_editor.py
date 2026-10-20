"""Pydantic schemas of the blog section editor routes (AE-0424, ADR-0025)."""

from pydantic import BaseModel, Field, field_validator

from rag_backend.domain.constants.blog_document import ERR_BLOG_IMAGE_ALT_BLANK
from rag_backend.domain.constants.blog_editor import IMAGE_PROMPT_MAX_CHARS

IMAGE_TEXT_MAX_CHARS = 500


class BlogImageGenerateRequest(BaseModel):
    """Generate/regenerate a cover or section image; ``prompt`` is the scene."""

    prompt: str | None = Field(default=None, max_length=IMAGE_PROMPT_MAX_CHARS)


class BlogImagePatchRequest(BaseModel):
    """Edit the alt text and/or caption of an existing image (never blank alt)."""

    alt: str | None = Field(default=None, max_length=IMAGE_TEXT_MAX_CHARS)
    caption: str | None = Field(default=None, max_length=IMAGE_TEXT_MAX_CHARS)

    @field_validator("alt")
    @classmethod
    def _alt_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError(ERR_BLOG_IMAGE_ALT_BLANK)
        return value


class BlogSectionRewriteRequest(BaseModel):
    """Rewrite one section in the persona voice (default persona when absent)."""

    persona_id: str | None = Field(default=None, max_length=36)


__all__ = [
    "BlogImageGenerateRequest",
    "BlogImagePatchRequest",
    "BlogSectionRewriteRequest",
]
