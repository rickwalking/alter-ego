"""Composition root for the autopilot module — manual constructor injection.

The inbound edge creates the request-scoped session (the unit of work) and
passes it here. This module does not look up a global container (ADR-0009 §9).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.protocols.social import SocialPublisher
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
    SystemClock,
)
from rag_backend.modules.autopilot.application.service import AutopilotService
from rag_backend.modules.autopilot.domain.publish import (
    ManualPublishCommand,
    ManualPublishOutcome,
)
from rag_backend.modules.autopilot.infrastructure.carousel_source import (
    PublishingCarouselSource,
)
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import gateway_for
from rag_backend.modules.autopilot.infrastructure.publish_notifier import (
    OutboxPublishNotifier,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)


@dataclass(frozen=True, kw_only=True)
class AutopilotBootstrapDeps:
    """Request-scoped wiring supplied by the inbound edge."""

    session: AsyncSession


def bootstrap_module(deps: AutopilotBootstrapDeps) -> AutopilotService:
    """Wire the repository to the application service for this session."""
    return AutopilotService(SqlAlchemyAutopilotRepository(deps.session))


@dataclass(frozen=True, kw_only=True)
class ManualInstagramPublishRequest:
    """Route inputs for one idempotent manual Instagram publish."""

    session: AsyncSession
    publisher: SocialPublisher
    project_id: str
    caption: str
    image_urls: tuple[str, ...]
    public_base_url: str


@dataclass(frozen=True, kw_only=True)
class InstagramTickConfig:
    """Worker-tick wiring. The session arrives on each tick."""

    publisher: SocialPublisher
    public_base_url: str


class InstagramPublishTickAdapter:
    """One publishing run per worker tick, on the tick's session."""

    def __init__(self, config: InstagramTickConfig) -> None:
        self._config = config

    async def tick(self, db: AsyncSession) -> int:
        """Publish or resume at most one run. Returns how many runs were touched."""
        job = _job(db, self._config.publisher, self._config.public_base_url)
        return await job.tick()


def build_instagram_publish_tick(
    config: InstagramTickConfig,
) -> InstagramPublishTickAdapter:
    """Build the worker collaborator from the process-wide publisher."""
    return InstagramPublishTickAdapter(config)


async def manual_instagram_publish(
    request: ManualInstagramPublishRequest,
) -> ManualPublishOutcome:
    """Run the publish job for the owner route, including the post-id short circuit."""
    job = _job(request.session, request.publisher, request.public_base_url)
    command = ManualPublishCommand(
        project_id=request.project_id,
        caption=request.caption,
        image_urls=request.image_urls,
    )
    return await job.publish_manual(command)


def _job(
    session: AsyncSession,
    publisher: SocialPublisher,
    public_base_url: str,
) -> InstagramPublishJob:
    repo = SqlAlchemyAutopilotRepository(session)
    deps = PublishJobDependencies(
        runs=repo,
        source=PublishingCarouselSource(session, public_base_url),
        gateway=gateway_for(publisher),
        notifier=OutboxPublishNotifier(session),
        clock=SystemClock(),
        checkpoint=repo,
    )
    return InstagramPublishJob(deps)
