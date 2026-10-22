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
    AutopilotRunnerTickAdapter,
    AutopilotTickConfig,
    CredentialRefreshTickAdapter,
    InstagramPublishTickAdapter,
    InstagramTickConfig,
    TelegramNotifyTickAdapter,
    TelegramTickConfig,
    build_autopilot_runner_tick,
    build_credential_refresh_tick,
    build_instagram_publish_tick,
    build_telegram_notify_tick,
    credential_tick_config,
    notifier_is_configured,
)

EngineFactory = Callable[[], EditorialWorkflowService]


@dataclass(frozen=True, kw_only=True)
class AutopilotWorkerSteps:
    """The autopilot collaborators handed to ``WorkflowWorkerServices``."""

    instagram_publish: InstagramPublishTickAdapter | None
    credential_refresh: CredentialRefreshTickAdapter | None
    autopilot_runner: AutopilotRunnerTickAdapter
    telegram_notify: TelegramNotifyTickAdapter


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
        autopilot_runner=build_autopilot_runner_tick(
            AutopilotTickConfig(
                owner_user_id=settings.autopilot_owner_user_id,
                persona_id=settings.autopilot_persona_id,
                autofix_attempts=settings.autopilot_autofix_attempts,
                autofix_escalation_attempts=(
                    settings.autopilot_autofix_escalation_attempts
                ),
                persona_unscored_max_ticks=(
                    settings.autopilot_persona_unscored_max_ticks
                ),
                engine_factory=engine_factory,
                stale_after_seconds=settings.workflow_run_heartbeat_stale_seconds,
                start_spacing_minutes=settings.autopilot_start_spacing_minutes,
                notifier_configured=notifier_is_configured(token, chat_id),
            )
        ),
        telegram_notify=build_telegram_notify_tick(
            TelegramTickConfig(
                token=token,
                chat_id=chat_id,
                web_base_url=settings.carousel_public_base_url,
                engine_factory=engine_factory,
            )
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
