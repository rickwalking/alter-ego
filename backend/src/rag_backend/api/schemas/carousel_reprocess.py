"""HTTP schemas for manual carousel recovery."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ManualReprocessRequest(BaseModel):
    """Project recovery fenced by the workspace lock version."""

    expected_version: int = Field(..., ge=1)
    run_id: UUID | None = None


class GenerationRunReprocessRequest(BaseModel):
    """Admin recovery with an optional project version fence."""

    expected_version: int | None = Field(default=None, ge=1)


class ManualReprocessResponse(BaseModel):
    """The accepted or existing durable run and honest maintenance result."""

    outcome: Literal["queued", "existing"]
    run_id: str
    status: str
    stuck_kind: str | None
    position: int | None
    eta_seconds: int | None
    lock_version: int | None
    worker_notified: bool
    last_error_code: str | None = None


class ManualRecoveryCapabilityResponse(BaseModel):
    """Workspace recovery capability and safe current-run progress."""

    can_reprocess: bool
    refusal_code: str | None
    stuck_kind: str | None
    run_id: str | None
    status: str | None
    last_phase: str | None
    last_error_code: str | None
    position: int | None
    eta_seconds: int | None
    lock_version: int | None


__all__ = [
    "GenerationRunReprocessRequest",
    "ManualRecoveryCapabilityResponse",
    "ManualReprocessRequest",
    "ManualReprocessResponse",
]
