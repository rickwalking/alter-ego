"""Build a publish snapshot from the publishing facade."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants import LANGUAGE_PT
from rag_backend.modules.autopilot.domain.ports import CarouselPublishSnapshot
from rag_backend.modules.publishing import (
    SlideImageUrlRequest,
    build_public_slide_image_urls,
    load_instagram_publish_target,
)


class PublishingCarouselSource:
    """Reads workflow, visibility, and public slide URLs for one carousel."""

    def __init__(self, session: AsyncSession, public_base_url: str) -> None:
        self._session = session
        self._public_base_url = public_base_url

    async def load(self, project_id: str) -> CarouselPublishSnapshot | None:
        """Return the snapshot, or None when the project does not exist."""
        target = await load_instagram_publish_target(self._session, project_id)
        if target is None:
            return None
        return CarouselPublishSnapshot(
            workflow_status=target.workflow_status,
            status=target.status,
            is_public=target.is_public,
            caption=target.caption,
            image_urls=_urls(self._public_base_url, project_id, target.slide_numbers),
            base_url_configured=bool(self._public_base_url),
        )


def _urls(base_url: str, project_id: str, numbers: tuple[int, ...]) -> tuple[str, ...]:
    if not base_url:
        return ()
    built = build_public_slide_image_urls(
        SlideImageUrlRequest(
            base_url=base_url,
            project_id=project_id,
            slide_numbers=numbers,
            language=LANGUAGE_PT,
        )
    )
    return tuple(built)
