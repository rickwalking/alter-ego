"""Wire the owner-action use case for one request session."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
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
from rag_backend.modules.autopilot.infrastructure.notice_source import SqlNoticeLogStore
from rag_backend.modules.autopilot.infrastructure.pending_rework import (
    SqlPendingReworkStore,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.run_recovery_store import (
    SqlRunRecoveryStore,
)
from rag_backend.modules.autopilot.infrastructure.telegram_reply import (
    ReplyClientConfig,
    TelegramOwnerMessenger,
)


@dataclass(frozen=True, kw_only=True)
class OwnerActionBuild:
    """Session, settings, and the editorial engine factory for one request."""

    session: AsyncSession
    settings: Settings
    engine_factory: EngineFactory


def build_owner_action_service(build: OwnerActionBuild) -> OwnerActionService:
    """Compose the webhook use case from the request session."""
    repo = SqlAlchemyAutopilotRepository(build.session)
    driver = InProcessEditorialDriver(
        EditorialDriverConfig(
            session=build.session,
            engine_factory=build.engine_factory,
            clock=SystemClock(),
            stale_after_seconds=build.settings.workflow_run_heartbeat_stale_seconds,
        )
    )
    token = build.settings.telegram_bot_token.get_secret_value()
    deps = OwnerActionDeps(
        runs=repo,
        updates=repo,
        pending=SqlPendingReworkStore(repo, SqlNoticeLogStore(build.session)),
        editorial=driver,
        release=PublishingCarouselReleaser(build.session),
        messenger=TelegramOwnerMessenger(ReplyClientConfig(token=token)),
        recovery=SqlRunRecoveryStore(build.session),
        clock=SystemClock(),
        owner_chat_id=build.settings.telegram_owner_chat_id,
        carousels=PublishingCarouselSource(
            build.session, build.settings.carousel_public_base_url
        ),
        default_publish=build.settings.autopilot_default_publish,
    )
    return OwnerActionService(deps)
