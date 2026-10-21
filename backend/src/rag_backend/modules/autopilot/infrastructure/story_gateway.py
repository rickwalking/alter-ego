"""Story Graph steps backed by ``MetaInstagramPublisher``.

Same host, token, and error translation as the carousel's stepped gateway.
Only the real Graph publisher can post a Story; any other publisher gets no
Story step.
"""

from __future__ import annotations

from rag_backend.domain.constants.instagram_publish import CONTAINER_STATUS_PUBLISHED
from rag_backend.domain.protocols.social import SocialPublisher
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisher,
)
from rag_backend.modules.autopilot.domain.publish import StoredContainer
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import guard_graph


class SteppedStoryGateway:
    """``STORIES`` container, ``status_code`` polls, then ``media_publish``."""

    def __init__(self, publisher: MetaInstagramPublisher) -> None:
        self._publisher = publisher

    async def open_story(self, image_url: str) -> str:
        """Create the Story container."""
        return await guard_graph(
            lambda: self._publisher.create_story_container(image_url)
        )

    async def was_published(self, container: StoredContainer) -> bool:
        """One status read for a container older than the reuse window."""
        status = await guard_graph(
            lambda: self._publisher.container_status(container.container_id)
        )
        return status == CONTAINER_STATUS_PUBLISHED

    async def finish_story(self, container: StoredContainer) -> str | None:
        """Poll until ready, then publish. None when it was already published.

        A Story is not listed on ``/media``, so the media id of a container
        that already reports ``PUBLISHED`` is not recovered.
        """
        status = await guard_graph(
            lambda: self._publisher.await_container(container.container_id)
        )
        if status == CONTAINER_STATUS_PUBLISHED:
            return None
        return await guard_graph(
            lambda: self._publisher.media_publish(container.container_id)
        )


def story_gateway_for(publisher: SocialPublisher) -> SteppedStoryGateway | None:
    """A Story gateway for the Graph publisher, else None (no Story step)."""
    if isinstance(publisher, MetaInstagramPublisher):
        return SteppedStoryGateway(publisher)
    return None
