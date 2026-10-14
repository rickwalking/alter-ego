"""Composition root for the autopilot module — manual constructor injection.

The inbound edge creates the request-scoped session (the unit of work) and
passes it here. This module does not look up a global container (ADR-0009 §9).
The app factory supplies the editorial engine factory for the worker tick.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.protocols.social import SocialPublisher
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.application.manual_publish import (
    ManualInstagramPublish,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
    SystemClock,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.application.service import AutopilotService
from rag_backend.modules.autopilot.application.signal_cache import SignalBundleCache
from rag_backend.modules.autopilot.application.signals_service import (
    SignalsService,
    SignalsServiceDependencies,
)
from rag_backend.modules.autopilot.constants import (
    COLLECTOR_TIMEOUT_SECONDS,
    SIGNAL_CACHE_TTL_SECONDS,
)
from rag_backend.modules.autopilot.domain.ports import RecordServedUrls
from rag_backend.modules.autopilot.domain.publish import (
    ManualPublishCommand,
    ManualPublishOutcome,
)
from rag_backend.modules.autopilot.domain.signals import SignalsBundle
from rag_backend.modules.autopilot.infrastructure.carousel_source import (
    PublishingCarouselSource,
)
from rag_backend.modules.autopilot.infrastructure.collectors.factory import (
    CollectorBuildConfig,
    build_collectors,
)
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import gateway_for
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.publish_claims import (
    SqlPublishClaims,
)
from rag_backend.modules.autopilot.infrastructure.publish_notifier import (
    OutboxPublishNotifier,
)
from rag_backend.modules.autopilot.infrastructure.ready_notifier import (
    OutboxReadyNotifier,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.run_recovery_store import (
    SqlRunRecoveryStore,
)

if TYPE_CHECKING:
    from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
        EngineFactory,
    )


@dataclass(frozen=True, kw_only=True)
class AutopilotBootstrapDeps:
    """Request-scoped wiring supplied by the inbound edge."""

    session: AsyncSession


def bootstrap_module(deps: AutopilotBootstrapDeps) -> AutopilotService:
    """Wire the repository to the application service for this session."""
    return AutopilotService(
        SqlAlchemyAutopilotRepository(deps.session),
        SqlPublishClaims(deps.session),
    )


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
    deps = _job_deps(request.session, request.publisher, request.public_base_url)
    command = ManualPublishCommand(
        project_id=request.project_id,
        caption=request.caption,
        image_urls=request.image_urls,
    )
    return await ManualInstagramPublish(deps).publish(command)


def _job(
    session: AsyncSession,
    publisher: SocialPublisher,
    public_base_url: str,
) -> InstagramPublishJob:
    return InstagramPublishJob(_job_deps(session, publisher, public_base_url))


def _job_deps(
    session: AsyncSession,
    publisher: SocialPublisher,
    public_base_url: str,
) -> PublishJobDependencies:
    repo = SqlAlchemyAutopilotRepository(session)
    return PublishJobDependencies(
        runs=repo,
        source=PublishingCarouselSource(session, public_base_url),
        gateway=gateway_for(publisher),
        notifier=OutboxPublishNotifier(session),
        clock=SystemClock(),
        checkpoint=repo,
        claims=SqlPublishClaims(session),
    )


_bundle_cache: SignalBundleCache | None = None


def default_signals_service() -> SignalsService:
    """Process-wide signals service. The cache is shared across requests."""
    global _bundle_cache
    if _bundle_cache is None:
        _bundle_cache = SignalBundleCache(SystemClock(), SIGNAL_CACHE_TTL_SECONDS)
    settings = get_settings()
    deps = SignalsServiceDependencies(
        collectors=build_collectors(_collector_config(settings)),
        clock=SystemClock(),
        cache=_bundle_cache,
        timeout_seconds=COLLECTOR_TIMEOUT_SECONDS,
    )
    return SignalsService(deps)


async def remember_served_signal_urls(
    session: AsyncSession,
    bundle: SignalsBundle,
    served_at: datetime,
) -> None:
    """Persist the bundle's URLs so topic intake can allowlist them for 6 hours."""
    store = SqlAlchemyTopicIntakeStore(session)
    urls = tuple(signal.url for signal in bundle.signals)
    await store.record_served_urls(RecordServedUrls(urls=urls, served_at=served_at))
    await store.commit()


@dataclass(frozen=True, kw_only=True)
class AutopilotTickConfig:
    """Worker-tick wiring for the editorial runner. The session arrives per tick."""

    owner_user_id: str
    engine_factory: EngineFactory
    stale_after_seconds: int
    notifier_configured: bool = True


class AutopilotRunnerTickAdapter:
    """One autopilot run step per worker tick, on the tick's session."""

    def __init__(self, config: AutopilotTickConfig) -> None:
        self._config = config

    async def tick(self, db: AsyncSession) -> int:
        """Advance at most one run. Returns 1 when a run was touched."""
        return await AutopilotRunner(_runner_deps(db, self._config)).tick()


def build_autopilot_runner_tick(
    config: AutopilotTickConfig,
) -> AutopilotRunnerTickAdapter:
    """Build the worker collaborator. The engine is constructed on each tick."""
    return AutopilotRunnerTickAdapter(config)


def _runner_deps(
    session: AsyncSession,
    config: AutopilotTickConfig,
) -> RunnerDependencies:
    from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
        EditorialDriverConfig,
        InProcessEditorialDriver,
    )

    repo = SqlAlchemyAutopilotRepository(session)
    driver = InProcessEditorialDriver(
        EditorialDriverConfig(
            session=session,
            engine_factory=config.engine_factory,
            clock=SystemClock(),
            stale_after_seconds=config.stale_after_seconds,
        )
    )
    return RunnerDependencies(
        runs=repo,
        topics=repo,
        editorial=driver,
        notices=OutboxReadyNotifier(session),
        recovery=SqlRunRecoveryStore(session),
        owner_user_id=config.owner_user_id,
        notifier_configured=config.notifier_configured,
    )


@dataclass(frozen=True, kw_only=True)
class TelegramTickConfig:
    """Worker-tick wiring for owner Telegram notices."""

    token: str
    chat_id: str
    web_base_url: str


class TelegramNotifyTickAdapter:
    """Deliver pending notices on the tick's session, after the runner."""

    def __init__(self, config: TelegramTickConfig) -> None:
        self._config = config

    async def tick(self, db: AsyncSession) -> int:
        """Send due reviews, statuses, and reminders."""
        from rag_backend.modules.autopilot.application.notifications import (
            NotificationDependencies,
            OwnerNotificationService,
        )
        from rag_backend.modules.autopilot.infrastructure.notice_source import (
            SqlAutopilotEventSource,
            SqlNoticeLogStore,
        )
        from rag_backend.modules.autopilot.infrastructure.review_facts import (
            CarouselReviewFacts,
        )
        from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
            AsyncSleeper,
            TelegramClientConfig,
            TelegramNotifier,
        )

        configured = bool(self._config.token.strip() and self._config.chat_id.strip())
        deps = NotificationDependencies(
            events=SqlAutopilotEventSource(db),
            runs=SqlAlchemyAutopilotRepository(db),
            facts=CarouselReviewFacts(db),
            notices=SqlNoticeLogStore(db),
            notifier=TelegramNotifier(
                TelegramClientConfig(token=self._config.token, sleeper=AsyncSleeper())
            ),
            clock=SystemClock(),
            chat_id=self._config.chat_id,
            configured=configured,
            web_base_url=self._config.web_base_url,
        )
        return await OwnerNotificationService(deps).tick()


def build_telegram_notify_tick(config: TelegramTickConfig) -> TelegramNotifyTickAdapter:
    """Build the worker collaborator. The HTTP client is created per process tick."""
    return TelegramNotifyTickAdapter(config)


def notifier_is_configured(token: str, chat_id: str) -> bool:
    """True when both Telegram settings are non-empty."""
    return bool(token.strip() and chat_id.strip())


def _collector_config(settings: Settings) -> CollectorBuildConfig:
    return CollectorBuildConfig(
        x_resolver=settings.autopilot_x_resolver,
        x_mirror_host=settings.autopilot_x_mirror_host,
        github_token=settings.github_token.get_secret_value(),
    )
