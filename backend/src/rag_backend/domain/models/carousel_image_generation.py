"""Domain model for carousel image generation attempts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

JsonScalar = str | int | float | bool


@dataclass
class CarouselImageGeneration:
    project_id: UUID
    slide_id: UUID
    slide_number: int
    generation_key: str
    status: str
    output_path: str | None = None
    prompt_hash: str | None = None
    provider: str | None = None
    model: str | None = None
    style: str | None = None
    raw_prompt: str | None = None
    rendered_prompt: str | None = None
    content_sha256: str | None = None
    provider_image_id: str | None = None
    error_json: dict[str, JsonScalar] | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
