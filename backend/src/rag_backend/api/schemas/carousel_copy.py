"""Schemas for saving a carousel's Instagram caption and LinkedIn posts."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from rag_backend.domain.constants.carousel_copy_edit import (
    ERR_COPY_EDIT_EMPTY,
    INSTAGRAM_CAPTION_MAX_CHARS,
    LINKEDIN_POST_MAX_CHARS,
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
