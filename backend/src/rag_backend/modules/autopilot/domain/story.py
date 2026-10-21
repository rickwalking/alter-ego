"""Instagram Story records, results, and ports. No I/O.

The Story announces a carousel that was just posted. It is optional: a
Story failure is recorded and told to the owner, never turned into a
publish failure. One row per carousel makes it idempotent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from rag_backend.modules.autopilot.domain.publish import PostExtras, StoredContainer


@dataclass(frozen=True, kw_only=True)
class StoryRecord:
    """The stored Story state of one carousel."""

    project_id: str
    state: str
    container: StoredContainer | None
    media_id: str | None
    error: str | None


@dataclass(frozen=True, kw_only=True)
class SaveStoryContainer:
    """Persist the Story container before ``media_publish``."""

    project_id: str
    container: StoredContainer


@dataclass(frozen=True, kw_only=True)
class SaveStoryResult:
    """Persist the Story's final state, its media id, or its error."""

    project_id: str
    state: str
    media_id: str | None
    error: str | None
    at: datetime


@dataclass(frozen=True, kw_only=True)
class StoryMedia:
    """The public Story image URL (None when it is missing) and the music facts."""

    image_url: str | None
    niche: str
    image_style: str


class StoryStore(Protocol):
    """The ``instagram_stories`` row of one carousel. The caller commits."""

    async def get(self, project_id: str) -> StoryRecord | None:
        """Return the record, or None when no Story was attempted."""
        ...

    async def save_container(self, command: SaveStoryContainer) -> None:
        """Store the container id and creation time."""
        ...

    async def save_result(self, command: SaveStoryResult) -> None:
        """Store the final state. Keeps the container."""
        ...


class StoryMediaSource(Protocol):
    """Renders the Story image and reads the facts the music nudge needs."""

    async def load(self, project_id: str) -> StoryMedia | None:
        """Return the media, or None when the carousel does not exist."""
        ...


class ContainerProbe(Protocol):
    """One status read of a stored container."""

    async def was_published(self, container: StoredContainer) -> bool:
        """True when the container reports ``PUBLISHED``."""
        ...


class StoryGateway(ContainerProbe, Protocol):
    """Graph calls for one Story."""

    async def open_story(self, image_url: str) -> str:
        """Create the ``STORIES`` container and return its id."""
        ...

    async def finish_story(self, container: StoredContainer) -> str | None:
        """Poll, then ``media_publish``. None when it was already ``PUBLISHED``."""
        ...


class StoryRunner(Protocol):
    """The publish job's view of the Story step."""

    async def run(self, project_id: str) -> PostExtras:
        """Post the Story once. Never raises."""
        ...
