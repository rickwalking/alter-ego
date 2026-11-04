"""HTTP schemas for the owner's carousel Retry."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CarouselRetryRequest(BaseModel):
    """A Retry fenced by the workspace lock version."""

    expected_version: int = Field(..., ge=1)


class CarouselRetryAcceptedResponse(BaseModel):
    """The accepted Retry: what it runs and the carousel's new state."""

    accepted: bool
    retry_kind: str
    current_phase: str
    phase_status: str
    lock_version: int | None
    autopilot_run_id: str | None = None


class CarouselRetryCapabilityResponse(BaseModel):
    """Whether a Retry would be accepted now, and as which kind."""

    can_retry: bool
    retry_kind: str | None = None
    refusal_code: str | None = None
    lock_version: int | None = None


__all__ = [
    "CarouselRetryAcceptedResponse",
    "CarouselRetryCapabilityResponse",
    "CarouselRetryRequest",
]
