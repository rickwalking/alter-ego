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
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
