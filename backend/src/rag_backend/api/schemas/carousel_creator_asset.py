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
    role: str | None = None
    pose_tag: str | None = None


class CreatorAssetSelectRequest(BaseModel):
    creator_asset_id: UUID = Field(..., description="Managed creator asset identifier")


class CreatorAssetListResponse(BaseModel):
    """The caller's photo library."""

    items: list[CreatorAssetResponse]


class HookPhotoResponse(BaseModel):
    """The project's slide-1 photo."""

    project_id: UUID
    hook_asset_id: UUID


__all__ = [
    "CreatorAssetListResponse",
    "CreatorAssetResponse",
    "CreatorAssetSelectRequest",
    "HookPhotoResponse",
]


class CreatorAssetUsageResponse(BaseModel):
    """A carousel that still uses a photo."""

    id: UUID
    title: str | None


class CreatorAssetTopicUsageResponse(BaseModel):
    """An autopilot cover that uses a photo; ``id`` is None until a topic claims it."""

    id: UUID | None
    title: str | None


class CreatorAssetInUseDetail(BaseModel):
    """The 409 ``detail`` of deleting a photo a carousel or autopilot cover uses."""

    code: str
    carousels: list[CreatorAssetUsageResponse]
    topics: list[CreatorAssetTopicUsageResponse]


class CreatorAssetInUseResponse(BaseModel):
    """The 409 body of deleting a photo a carousel still uses."""

    detail: CreatorAssetInUseDetail
