"""API schemas for managed carousel creator assets."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreatorAssetResponse(BaseModel):
    id: UUID
    owner_id: str
    content_sha256: str
    media_type: str
    width: int
    height: int
    relative_path: str
    staged_relative_path: str
    created_at: datetime
    updated_at: datetime


class CreatorAssetSelectRequest(BaseModel):
    creator_asset_id: UUID = Field(..., description="Managed creator asset identifier")


__all__ = ["CreatorAssetResponse", "CreatorAssetSelectRequest"]
