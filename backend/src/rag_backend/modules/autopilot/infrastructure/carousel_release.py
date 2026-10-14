"""Set ``is_public`` through the publishing facade (AE-0356)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.owner_ports import ReleaseCommand
from rag_backend.modules.editorial.public import CarouselAutomationAcl
from rag_backend.modules.publishing.public import (
    AclCarouselReleaseAdapter,
    CarouselReleaseCommand,
    CarouselReleaseHandler,
    LegacyPublishingAcl,
)


class PublishingCarouselReleaser:
    """Loads the carousel and releases it with ``CarouselReleaseCommand``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def release(self, command: ReleaseCommand) -> bool:
        """True when the project existed and the public-release write ran."""
        carousels = CarouselAutomationAcl(self._session)
        project = await carousels.load_project(command.project_id)
        if project is None:
            return False
        acl = LegacyPublishingAcl(self._session, carousels.repository)
        handler = CarouselReleaseHandler(AclCarouselReleaseAdapter(acl))
        await handler.release(
            CarouselReleaseCommand(project=project, project_id=command.project_id)
        )
        return True
