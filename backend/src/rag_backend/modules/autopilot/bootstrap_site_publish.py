"""Wire the site's "Publicar agora" approval (kept apart from the webhook wiring).

The webhook bootstrap imports the API layer (boost limits); this module does not,
so the public facade can build the site approval without crossing layers.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.site_publish import (
    SitePublishApproval,
    SitePublishDeps,
)
from rag_backend.modules.autopilot.infrastructure.carousel_release import (
    PublishingCarouselReleaser,
)
from rag_backend.modules.autopilot.infrastructure.carousel_source import (
    PublishingCarouselSource,
)
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    EngineFactory,
    InProcessEditorialDriver,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)


@dataclass(frozen=True, kw_only=True)
class EditorialBuild:
    """Session, settings, and the editorial engine factory for one request."""

    session: AsyncSession
    settings: Settings
    engine_factory: EngineFactory


def editorial_driver(build: EditorialBuild) -> InProcessEditorialDriver:
    """The in-process editorial driver on the request session."""
    return InProcessEditorialDriver(
        EditorialDriverConfig(
            session=build.session,
            engine_factory=build.engine_factory,
            clock=SystemClock(),
            stale_after_seconds=build.settings.workflow_run_heartbeat_stale_seconds,
        )
    )


def build_site_publish_approval(build: EditorialBuild) -> SitePublishApproval:
    """The site's "Publicar agora" approval, on the request session."""
    approval = FinalReviewApproval(
        editorial=editorial_driver(build),
        release_port=PublishingCarouselReleaser(build.session),
        carousels=PublishingCarouselSource(
            build.session, build.settings.carousel_public_base_url
        ),
    )
    return SitePublishApproval(
        SitePublishDeps(
            runs=SqlAlchemyAutopilotRepository(build.session), approval=approval
        )
    )


__all__ = ["EditorialBuild", "build_site_publish_approval", "editorial_driver"]
