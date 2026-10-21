"""Schemas for the completed-project slide-text edit endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rag_backend.api.schemas.carousel_workflow import LocalizedSlideReview
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationReport,
    ViolationSeverity,
)


class CarouselSlideEditRequest(BaseModel):
    """Reviewer text edits for a completed carousel's slides (no image regen)."""

    edited_slides: list[LocalizedSlideReview] = Field(..., min_length=1)


class SlideFieldViolation(BaseModel):
    """One violation addressed to the form field it belongs to.

    ``item_list``/``item_index``/``item_field`` are set for structured items
    (e.g. ``summary_points`` item 0 ``body``) and ``None`` for heading/body.
    """

    code: str
    message: str
    severity: ViolationSeverity
    slide_index: int | None = None
    locale: str | None = None
    field: str | None = None
    item_list: str | None = None
    item_index: int | None = None
    item_field: str | None = None


class CarouselSlideEditResponse(BaseModel):
    """Result of a completed-project slide edit: fresh report + republish marker.

    ``field_violations`` restates ``validation.violations`` per form
    field (additive; ``validation`` keeps its contract).
    """

    project_id: str
    status: str
    validation: SlideValidationReport
    needs_republish: bool = False
    updated_slides: list[int] = Field(default_factory=list)
    field_violations: list[SlideFieldViolation] = Field(default_factory=list)


__all__ = [
    "CarouselSlideEditRequest",
    "CarouselSlideEditResponse",
    "SlideFieldViolation",
]
