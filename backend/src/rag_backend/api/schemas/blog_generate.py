"""Schemas of the blog generation entry points (AE-0425, ADR-0025)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

BlogLanguage = Literal["pt", "en"]

TOPIC_MIN_CHARS = 3
TOPIC_MAX_CHARS = 500
MAX_SOURCE_URLS = 10


class BlogFromCarouselRequest(BaseModel):
    """``POST /blog-posts/from-carousel``: always creates a draft."""

    project_id: UUID
    persona_id: UUID | None = None
    # The document is always PT canonical + an EN translation; ``language``
    # records which one the owner asked to edit first.
    language: BlogLanguage = "pt"


class BlogGenerateRequest(BaseModel):
    """``POST /blog-posts/generate``: a standalone draft from a topic."""

    topic: str = Field(..., min_length=TOPIC_MIN_CHARS, max_length=TOPIC_MAX_CHARS)
    persona_id: UUID | None = None
    language: BlogLanguage = "pt"
    # References for the writer; never fetched by the backend (no SSRF).
    source_urls: list[HttpUrl] = Field(default_factory=list, max_length=MAX_SOURCE_URLS)


class BlogGenerationState(BaseModel):
    """The run state returned by the 202 (the editor then polls ``GET``)."""

    status: str
    attempt: int
    warnings: list[str] = Field(default_factory=list)


class BlogGenerationAccepted(BaseModel):
    """202 body: the draft row id and its generation state."""

    id: str
    generation: BlogGenerationState


class BlogGenerationConflict(BaseModel):
    """409 body of ``from-carousel`` when the project already has a blog row."""

    code: str
    post_id: str


__all__ = [
    "BlogFromCarouselRequest",
    "BlogGenerateRequest",
    "BlogGenerationAccepted",
    "BlogGenerationConflict",
    "BlogGenerationState",
]
