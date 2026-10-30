"""HTTP bodies for the boost routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BoostAudienceBody(BaseModel):
    """Countries and ages. Interests are rejected by extra=forbid."""

    model_config = ConfigDict(extra="forbid")
    countries: list[str] = Field(default_factory=lambda: ["BR"])
    age_min: int = Field(default=18, ge=18, le=65)
    age_max: int = Field(default=65, ge=18, le=65)


class BoostRequestCreate(BaseModel):
    """What the bot is allowed to ask for."""

    model_config = ConfigDict(extra="forbid")
    media_id: str = Field(pattern=r"^\d{5,32}$")
    daily_budget_cents: int = Field(gt=0)
    days: int = Field(ge=1)
    objective: str = "engagement"
    audience: BoostAudienceBody = Field(default_factory=BoostAudienceBody)
    reason: str = Field(min_length=1, max_length=600)
    score: float | None = None
    start_at: datetime | None = None


class BoostRequestResponse(BaseModel):
    """One stored request. Ad insights come from the database only."""

    id: UUID
    status: str
    media_id: str
    permalink: str | None
    objective: str
    daily_budget_cents: int
    days: int
    total_budget_cents: int
    currency: str
    reason: str
    created_at: datetime
    expires_at: datetime
    error_code: str | None
    meta_campaign_id: str | None = None
    meta_ad_id: str | None = None


class BoostRequestList(BaseModel):
    """Newest first."""

    items: list[BoostRequestResponse]


__all__ = [
    "BoostRequestCreate",
    "BoostRequestList",
    "BoostRequestResponse",
]
