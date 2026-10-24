"""Schemas for generating a slide-1 cover from library photos with Grok."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag_backend.domain.constants.cover_generation import (
    COVER_GENERATION_MAX_PHOTOS,
    COVER_GENERATION_MIN_PHOTOS,
    COVER_GENERATION_PROMPT_MAX_LEN,
    COVER_GENERATION_PROMPT_MIN_LEN,
    ERR_COVER_GENERATION_PROMPT,
)


class CoverGenerationRequest(BaseModel):
    """The photos to send, the owner's direction and the explicit confirmation."""

    model_config = ConfigDict(extra="forbid")

    photo_ids: list[UUID] = Field(
        ...,
        min_length=COVER_GENERATION_MIN_PHOTOS,
        max_length=COVER_GENERATION_MAX_PHOTOS,
    )
    prompt: str = Field(
        ...,
        min_length=COVER_GENERATION_PROMPT_MIN_LEN,
        max_length=COVER_GENERATION_PROMPT_MAX_LEN,
    )
    confirmed: bool

    @field_validator("prompt")
    @classmethod
    def _check_prompt(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < COVER_GENERATION_PROMPT_MIN_LEN:
            raise ValueError(ERR_COVER_GENERATION_PROMPT)
        return stripped

    @field_validator("photo_ids")
    @classmethod
    def _distinct(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))


class CoverGenerationResponse(BaseModel):
    """One generation: its status, failure code and resulting cover."""

    id: UUID
    status: str = Field(..., description="pending | succeeded | failed")
    error_code: str | None = None
    error_detail: str | None = Field(
        None, description="The Grok Bot's own failure message, when it sent one"
    )
    asset_id: UUID | None = None
    created_at: datetime
    completed_at: datetime | None = None


class CoverGenerationsResponse(BaseModel):
    """The caps in use and the carousel's generations, newest first.

    ``*_used`` count pending and succeeded generations; ``*_attempts`` count
    every attempt, failures included, against the hard attempt ceiling.
    """

    carousel_used: int
    carousel_cap: int
    month_used: int
    month_cap: int
    carousel_attempts: int
    carousel_attempt_cap: int
    month_attempts: int
    month_attempt_cap: int
    generations: list[CoverGenerationResponse]


__all__ = [
    "CoverGenerationRequest",
    "CoverGenerationResponse",
    "CoverGenerationsResponse",
]
