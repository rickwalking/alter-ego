"""Schemas for the publish-step slide-1 cover picker (AE-0445)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CoverOptionResponse(BaseModel):
    """One image slide 1 may show: a library photo or the GrokBot offer."""

    asset_id: UUID
    source: str = Field(..., description="library | offer")
    kind: str = Field("", description="GrokBot cover kind (ai_image | screenshot)")


class CoverOptionsResponse(BaseModel):
    """The current slide-1 image and the options, library photos first."""

    project_id: str
    current_asset_id: UUID | None
    options: list[CoverOptionResponse]


class CoverPickRequest(BaseModel):
    """The chosen asset and the workflow lock version the page read."""

    asset_id: UUID
    expected_version: int = Field(..., ge=1)


class CoverPickResponse(BaseModel):
    """The switch was stored and the slides + PDFs re-rendered."""

    project_id: str
    status: str
    current_asset_id: UUID | None
    artifact_version: str | None = None


__all__ = [
    "CoverOptionResponse",
    "CoverOptionsResponse",
    "CoverPickRequest",
    "CoverPickResponse",
]
