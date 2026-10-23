"""Schemas for saving a carousel's Instagram caption and LinkedIn posts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from rag_backend.domain.constants.carousel_copy_edit import (
    ERR_COPY_EDIT_EMPTY,
    INSTAGRAM_CAPTION_MAX_CHARS,
    LINKEDIN_POST_MAX_CHARS,
)
from rag_backend.domain.constants.carousel_copy_versions import (
    VERSIONS_PAGE_DEFAULT,
    VERSIONS_PAGE_MAX,
)


class CarouselCopyUpdateRequest(BaseModel):
    """The texts to save; a missing (or null) field keeps its saved text."""

    caption: str | None = Field(default=None, max_length=INSTAGRAM_CAPTION_MAX_CHARS)
    linkedin_post_pt: str | None = Field(
        default=None, max_length=LINKEDIN_POST_MAX_CHARS
    )
    linkedin_post_en: str | None = Field(
        default=None, max_length=LINKEDIN_POST_MAX_CHARS
    )

    @model_validator(mode="after")
    def _require_one_text(self) -> CarouselCopyUpdateRequest:
        """Reject a save that carries no text at all."""
        texts = (self.caption, self.linkedin_post_pt, self.linkedin_post_en)
        if all(text is None for text in texts):
            raise ValueError(ERR_COPY_EDIT_EMPTY)
        return self


class CarouselCopyResponse(BaseModel):
    """The saved texts and the lock version the next save must send."""

    project_id: UUID
    caption: str | None
    linkedin_post_pt: str | None
    linkedin_post_en: str | None
    lock_version: int


class CarouselCopyVersionResponse(BaseModel):
    """One stored version of the caption or a LinkedIn post.

    ``author_id`` / ``author_name`` are null for the generated text kept on the
    first edit; ``restored_from`` names the version a restore brought back.
    """

    version_number: int
    field: str
    text: str
    author_id: str | None
    author_name: str | None
    created_at: datetime
    restored_from: int | None = None


class CarouselCopyVersionsResponse(BaseModel):
    """One page of the carousel's caption / LinkedIn versions, newest first.

    ``next_before`` is the ``before`` of the next (older) page, or null when this
    page is the last.
    """

    project_id: UUID
    versions: list[CarouselCopyVersionResponse]
    next_before: int | None = None


class VersionPageQuery(BaseModel):
    """``limit`` versions (default 50, at most 200), older than ``before``."""

    limit: int = Field(VERSIONS_PAGE_DEFAULT, ge=1, le=VERSIONS_PAGE_MAX)
    before: int | None = Field(None, ge=1)
