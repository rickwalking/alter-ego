"""Autopilot worker-step wiring for the composition root.

Split from ``app_factory`` so that file stays under 400 lines. Builds the
editorial engine factory and the four autopilot worker collaborators.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.container import container
from rag_backend.infrastructure.events.factory import get_event_publisher
from rag_backend.modules.autopilot import (
    AutopilotTickConfig,
    CredentialRefreshTickAdapter,
    InstagramPublishTickAdapter,
    InstagramTickConfig,
    TelegramNotifyTickAdapter,
    TelegramTickConfig,
    build_credential_refresh_tick,
    build_instagram_publish_tick,
    build_telegram_notify_tick,
    credential_tick_config,
    notifier_is_configured,
)
from rag_backend.modules.autopilot.application.boost_tick import (
    BoostTick,
    BoostTickDeps,
)

EngineFactory = Callable[[], EditorialWorkflowService]


@dataclass(frozen=True, kw_only=True)
class AutopilotWorkerSteps:
    """The autopilot collaborators handed to ``WorkflowWorkerServices``."""

    instagram_publish: InstagramPublishTickAdapter | None
    credential_refresh: CredentialRefreshTickAdapter | None
    telegram_notify: TelegramNotifyTickAdapter
    boost: BoostRunAdapter | None


def autopilot_engine_factory(checkpointer: object | None) -> EngineFactory:
    """Editorial engine for one autopilot tick. Uses the process container."""

    def build() -> EditorialWorkflowService:
        settings = get_settings()
        publisher = get_event_publisher(settings.redis_url or None)
        research = None
        if settings.research_enrichment_enabled:
            research = container.research_tool()
        return EditorialWorkflowService(
            EditorialWorkflowConfig(
                llm=container.llm_service().role_models,
                checkpointer=checkpointer,
                event_service=WorkflowEventService(publisher),
                image_registry=container.image_provider_registry(),
                research_tool=research,
            )
        )

    return build


def build_autopilot_worker_steps(
    settings: Settings,
    engine_factory: EngineFactory,
) -> AutopilotWorkerSteps:
    """Publish, token refresh, runner, and Telegram steps for the worker loop."""
    token = settings.telegram_bot_token.get_secret_value()
    chat_id = settings.telegram_owner_chat_id
    return AutopilotWorkerSteps(
        instagram_publish=instagram_publish_step(settings),
        credential_refresh=credential_refresh_step(settings),
        telegram_notify=build_telegram_notify_tick(
            TelegramTickConfig(
                token=token,
                chat_id=chat_id,
                web_base_url=settings.carousel_public_base_url,
                engine_factory=engine_factory,
            )
        ),
        boost=BoostRunAdapter(settings),
    )


def autopilot_tick_config(
    settings: Settings, engine_factory: EngineFactory
) -> AutopilotTickConfig:
    """The runner wiring, shared by the web tick and the generation worker."""
    token = settings.telegram_bot_token.get_secret_value()
    return AutopilotTickConfig(
        owner_user_id=settings.autopilot_owner_user_id,
        cover_consent=settings.autopilot_cover_consent,
        persona_id=settings.autopilot_persona_id,
        autofix_attempts=settings.autopilot_autofix_attempts,
        autofix_escalation_attempts=settings.autopilot_autofix_escalation_attempts,
        persona_unscored_max_ticks=settings.autopilot_persona_unscored_max_ticks,
        engine_factory=engine_factory,
        stale_after_seconds=settings.workflow_run_heartbeat_stale_seconds,
        start_spacing_minutes=settings.autopilot_start_spacing_minutes,
        daily_cap=settings.autopilot_daily_cap,
        notifier_configured=notifier_is_configured(
            token, settings.telegram_owner_chat_id
        ),
    )


def instagram_publish_step(settings: Settings) -> InstagramPublishTickAdapter | None:
    """The publish worker, or None when the token cannot be decrypted."""
    if credential_tick_config(settings) is None:
        return None
    return build_instagram_publish_tick(
        InstagramTickConfig(
            publisher=container.instagram_publisher(),
            public_base_url=settings.carousel_public_base_url,
        )
    )


def credential_refresh_step(settings: Settings) -> CredentialRefreshTickAdapter | None:
    """The daily token refresher, or None when the Fernet key is unusable."""
    config = credential_tick_config(settings)
    if config is None:
        return None
    return build_credential_refresh_tick(config)


class BoostRunAdapter:
    """Expire pending boosts. Launch only when the spend switch is on."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def tick(self, db: object) -> int:
        from sqlalchemy.ext.asyncio import AsyncSession

        if not isinstance(db, AsyncSession):
            return 0
        ads, client = _ads_client(self._settings)
        try:
            return await _boost_tick(self._settings, db, ads).run()
        finally:
            await _close(client)


def _boost_tick(settings: Settings, db: object, ads: object) -> BoostTick:
    from sqlalchemy.ext.asyncio import AsyncSession

    from rag_backend.modules.autopilot.api.boost import limits_from
    from rag_backend.modules.autopilot.application.boost_requests import BoostDeps
    from rag_backend.modules.autopilot.application.publish_job import SystemClock
    from rag_backend.modules.autopilot.infrastructure.boost_notifier import (
        TelegramBoostMessenger,
    )
    from rag_backend.modules.autopilot.infrastructure.boost_store import SqlBoostStore
    from rag_backend.modules.autopilot.infrastructure.meta_ads_gateway import (
        MetaAdsGateway,
    )

    if not isinstance(db, AsyncSession):
        raise TypeError(type(db).__name__)
    gateway = ads if isinstance(ads, MetaAdsGateway) else None
    return BoostTick(
        BoostTickDeps(
            boosts=BoostDeps(
                store=SqlBoostStore(db),
                messenger=TelegramBoostMessenger(
                    token=settings.telegram_bot_token.get_secret_value(),
                    chat_id=settings.telegram_owner_chat_id,
                ),
                clock=SystemClock(),
                owner_chat_id=settings.telegram_owner_chat_id,
            ),
            limits=limits_from(settings),
            ads=gateway,
        )
    )


def _ads_client(settings: Settings) -> tuple[object, object]:
    import httpx

    from rag_backend.modules.autopilot.infrastructure.meta_ads_gateway import (
        AdsConfig,
        MetaAdsGateway,
    )

    token = settings.meta_ads_access_token.get_secret_value().strip()
    if not settings.boost_enabled or token == "":
        return None, None
    client = httpx.AsyncClient(timeout=20)
    gateway = MetaAdsGateway(
        AdsConfig(
            enabled=True,
            token=token,
            app_secret=settings.meta_ads_app_secret.get_secret_value().strip(),
            account_id=settings.meta_ad_account_id,
            page_id=settings.meta_page_id,
            ig_user_id=settings.meta_ads_ig_user_id,
            graph_base=settings.meta_ads_graph_base,
        ),
        client,
    )
    return gateway, client


async def _close(client: object) -> None:
    close = getattr(client, "aclose", None)
    if close is None:
        return
    await close()
