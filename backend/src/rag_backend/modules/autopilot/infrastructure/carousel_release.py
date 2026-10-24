"""Set ``is_public`` through the publishing facade."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
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
        """True when the project existed and the public-release write ran.

        A release that kept losing its ``lock_version`` compare-and-set is False,
        so the caller fails the approve and tells the owner.
        """
        carousels = CarouselAutomationAcl(self._session)
        project = await carousels.load_project(command.project_id)
        if project is None:
            return False
        acl = LegacyPublishingAcl(self._session, carousels.repository)
        handler = CarouselReleaseHandler(AclCarouselReleaseAdapter(acl))
        try:
            await handler.release(
                CarouselReleaseCommand(project=project, project_id=command.project_id)
            )
        except ValueError as exc:
            if str(exc) != ERR_VERSION_CONFLICT:
                raise
            return False
        return True
