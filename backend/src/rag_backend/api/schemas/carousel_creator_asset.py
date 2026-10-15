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
    # AE-0376: photo library role and pose tag.
    role: str | None = None
    pose_tag: str | None = None


class CreatorAssetSelectRequest(BaseModel):
    creator_asset_id: UUID = Field(..., description="Managed creator asset identifier")


class CreatorAssetListResponse(BaseModel):
    """AE-0376: the caller's photo library."""

    items: list[CreatorAssetResponse]


class HookPhotoResponse(BaseModel):
    """AE-0376: the project's slide-1 photo."""

    project_id: UUID
    hook_asset_id: UUID


__all__ = [
    "CreatorAssetListResponse",
    "CreatorAssetResponse",
    "CreatorAssetSelectRequest",
    "HookPhotoResponse",
]
