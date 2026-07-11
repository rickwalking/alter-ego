"""Response schemas for the deterministic carousel repair endpoint (AE-0311)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rag_backend.domain.models.carousel_presentation import SlideValidationReport


class RepairSlideDiffResponse(BaseModel):
    """Per-slide/locale repair outcome: fixed vs still-remaining rule codes."""

    slide_index: int | None = None
    locale: str | None = None
    repaired: bool = False
    repaired_codes: list[str] = Field(default_factory=list)
    remaining_codes: list[str] = Field(default_factory=list)


class CarouselRepairResponse(BaseModel):
    """Result of a deterministic repair: per-slide diffs + fresh report."""

    project_id: str
    status: str
    repaired: list[RepairSlideDiffResponse] = Field(default_factory=list)
    validation: SlideValidationReport
    needs_republish: bool = False


__all__ = ["CarouselRepairResponse", "RepairSlideDiffResponse"]
