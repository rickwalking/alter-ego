"""Domain model for managed carousel creator assets."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from rag_backend.domain.clock import utc_now


@dataclass
class CarouselCreatorAsset:
    """A managed creator asset; ``role`` is its photo-library role (hook/cta/pov)."""

    owner_id: str
    content_sha256: str
    media_type: str
    width: int
    height: int
    relative_path: str
    id: UUID = field(default_factory=uuid4)
    role: str | None = None
    pose_tag: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class CreatorAssetLibraryQuery:
    """List an owner's photo library, optionally by role."""

    owner_id: str
    role: str | None = None
    limit: int = 100


@dataclass(frozen=True)
class CreatorAssetTags:
    """An asset's library role (hook / cta / pov) and pose tag."""

    asset_id: UUID
    role: str | None = None
    pose_tag: str | None = None
