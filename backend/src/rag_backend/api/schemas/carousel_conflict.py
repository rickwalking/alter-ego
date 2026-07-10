"""Typed conflict-detail response schema for carousel 409s (AE-0316)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from rag_backend.domain.models.carousel_conflict import CarouselConflict


class CarouselConflictDetail(BaseModel):
    """Structured conflict payload served alongside the legacy detail."""

    code: str = Field(description="Machine-readable conflict cause")
    message: str = Field(description="Human-readable explanation")
    run_started_at: datetime | None = Field(
        default=None,
        description="Start of the active run for run-in-progress conflicts",
    )
    phase: str | None = Field(
        default=None,
        description="Charged workflow phase for revision-cap conflicts",
    )

    @classmethod
    def from_domain(cls, conflict: CarouselConflict) -> CarouselConflictDetail:
        """Map the domain conflict onto the response schema."""
        return cls(
            code=conflict.code,
            message=conflict.message,
            run_started_at=conflict.run_started_at,
            phase=conflict.phase,
        )


class CarouselConflictResponse(BaseModel):
    """Response body for carousel 409s: legacy string + structured payload.

    ``detail`` stays the historical machine-readable string so existing
    clients that string-compare it are unaffected; ``conflict`` is the
    additive structured payload for new consumers.
    """

    detail: str = Field(description="Legacy machine-readable detail string")
    conflict: CarouselConflictDetail


__all__ = ["CarouselConflictDetail", "CarouselConflictResponse"]
