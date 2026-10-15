"""Domain model for managed carousel creator assets."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class CarouselCreatorAsset:
    owner_id: str
    content_sha256: str
    media_type: str
    width: int
    height: int
    relative_path: str
    id: UUID = field(default_factory=uuid4)
    # AE-0373: photo library role (hook / cta / pov) and an optional pose tag.
    role: str | None = None
    pose_tag: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class CreatorAssetLibraryQuery:
    """AE-0376: list an owner's photo library, optionally by role."""

    owner_id: str
    role: str | None = None
    limit: int = 100


@dataclass(frozen=True)
class CreatorAssetTags:
    """AE-0376: an asset's library role (hook / cta / pov) and pose tag."""

    asset_id: UUID
    role: str | None = None
    pose_tag: str | None = None
