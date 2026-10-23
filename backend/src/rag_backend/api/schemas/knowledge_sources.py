"""Response schemas of the Knowledge Base carousel-sources listing."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

CAROUSEL_SOURCES_DEFAULT_LIMIT = 20
CAROUSEL_SOURCES_MAX_LIMIT = 100


class CarouselSourceItem(BaseModel):
    """One content source of a carousel, without its body."""

    id: UUID
    title: str
    source_type: str
    url: str | None = None
    project_id: UUID
    project_title: str
    created_at: datetime


class CarouselSourceFacet(BaseModel):
    """A carousel that has sources, for the carousel filter."""

    project_id: UUID
    title: str
    count: int


class CarouselSourceListResponse(BaseModel):
    """A page of carousel sources, its total and the carousels behind them."""

    items: list[CarouselSourceItem]
    total: int
    limit: int
    offset: int
    carousels: list[CarouselSourceFacet]
