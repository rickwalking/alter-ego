"""Domain model for carousel artifact build records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

JsonScalar = str | int | float | bool


@dataclass
class CarouselArtifactBuild:
    project_id: UUID
    artifact_version: str
    operation_id: str
    source_lock_version: int
    status: str
    attempt_count: int = 1
    staging_path: str | None = None
    error_json: dict[str, JsonScalar] | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
