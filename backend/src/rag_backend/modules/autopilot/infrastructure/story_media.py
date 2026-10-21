"""The Story image URL and the music facts, from the publishing facade."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.story import StoryMedia
from rag_backend.modules.publishing import (
    build_public_story_image_url,
    prepare_story_image,
)


class PublishingStoryMedia:
    """Renders ``story_pt.jpg`` and returns its public URL."""

    def __init__(self, session: AsyncSession, public_base_url: str) -> None:
        self._session = session
        self._public_base_url = public_base_url

    async def load(self, project_id: str) -> StoryMedia | None:
        """None when the carousel does not exist. The URL is None without an image."""
        target = await prepare_story_image(self._session, project_id)
        if target is None:
            return None
        image_url: str | None = None
        if target.ready and self._public_base_url:
            image_url = build_public_story_image_url(self._public_base_url, project_id)
        return StoryMedia(
            image_url=image_url,
            niche=target.niche,
            image_style=target.image_style,
        )
