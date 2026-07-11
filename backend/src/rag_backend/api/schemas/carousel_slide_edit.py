"""Schemas for the completed-project slide-text edit endpoint (AE-0314)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rag_backend.api.schemas.carousel_workflow import LocalizedSlideReview
from rag_backend.domain.models.carousel_presentation import SlideValidationReport


class CarouselSlideEditRequest(BaseModel):
    """Reviewer text edits for a completed carousel's slides (no image regen)."""

    edited_slides: list[LocalizedSlideReview] = Field(..., min_length=1)


class CarouselSlideEditResponse(BaseModel):
    """Result of a completed-project slide edit: fresh report + republish marker."""

    project_id: str
    status: str
    validation: SlideValidationReport
    needs_republish: bool = False
    updated_slides: list[int] = Field(default_factory=list)


__all__ = ["CarouselSlideEditRequest", "CarouselSlideEditResponse"]
