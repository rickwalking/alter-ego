"""Response schema of the carousel archive and restore routes."""

from datetime import datetime

from pydantic import BaseModel


class CarouselArchiveResponse(BaseModel):
    """A carousel's archive state after an archive or a restore."""

    id: str
    archived: bool
    archived_at: datetime | None = None
