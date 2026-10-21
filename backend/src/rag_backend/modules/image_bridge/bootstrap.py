"""Composition root of the image bridge module.

``build_carousel_openai_service`` is what the container hands to the image
provider registry as its OpenAI service: the plain OpenAI service when the
bridge is off or misconfigured (no behavior change), the Grok Bot bridge with
the OpenAI fallback when it is on.
"""

from __future__ import annotations

from rag_backend.domain.protocols import ImageGenerationService
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.image_bridge.application.callback import (
    CallbackDeps,
    ImageBridgeCallbackService,
)
from rag_backend.modules.image_bridge.application.fallback_image_service import (
    FallbackImageConfig,
    FallbackImageService,
)
from rag_backend.modules.image_bridge.application.grokbot_image_service import (
    GrokBotImageConfig,
    GrokBotImageDeps,
    GrokBotImageService,
)
from rag_backend.modules.image_bridge.constants import (
    CONFIG_NAMES_SEPARATOR,
    ENV_PUBLIC_BASE_URL,
    ENV_WEBHOOK_URL,
    ERR_CONFIG_MISSING,
    LOG_MISCONFIGURED,
    PROVIDER_OPENAI,
)
from rag_backend.modules.image_bridge.domain.exceptions import ImageBridgeConfigError
from rag_backend.modules.image_bridge.infrastructure.clock import SystemClock
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from rag_backend.modules.image_bridge.infrastructure.repository import (
    SqlImageBridgeJobRepository,
)
from rag_backend.modules.image_bridge.infrastructure.webhook_client import (
    HttpxGrokBotWebhook,
    WebhookClientConfig,
)

logger = get_logger()


def missing_image_bridge_settings(settings: Settings) -> list[str]:
    """Env names of the bridge URLs that are empty (values never returned)."""
    values = (
        (ENV_WEBHOOK_URL, settings.grokbot_image_webhook_url.get_secret_value()),
        (ENV_PUBLIC_BASE_URL, settings.image_bridge_public_base_url),
    )
    return [name for name, value in values if not value.strip()]


def report_image_bridge_config(settings: Settings) -> bool:
    """Startup check: whether the bridge will be wired.

    Prod auto-deploys on merge, so a missing secret must never crash-loop the
    backend: an enabled bridge without its URLs logs one ERROR naming the
    missing settings and the container keeps the plain OpenAI service.
    """
    if not settings.image_bridge_enabled:
        return False
    missing = missing_image_bridge_settings(settings)
    if not missing:
        return True
    logger.error(
        LOG_MISCONFIGURED,
        missing=missing,
        image_provider=PROVIDER_OPENAI,
    )
    return False


def build_carousel_openai_service(
    settings: Settings, openai_service: ImageGenerationService
) -> ImageGenerationService:
    """The OpenAI-slot service for the registry, bridged when enabled.

    Disabled, or enabled without its URLs (logged at startup by
    ``report_image_bridge_config``), keeps the plain OpenAI service.
    """
    if not settings.image_bridge_enabled or missing_image_bridge_settings(settings):
        return openai_service
    primary = GrokBotImageService(_waiter_deps(settings), _waiter_config(settings))
    return FallbackImageService(
        FallbackImageConfig(
            primary=primary,
            fallback=openai_service,
            fallback_enabled=settings.image_bridge_fallback_enabled,
        )
    )


def build_grokbot_image_service(settings: Settings) -> ImageGenerationService:
    """The bridge alone, without the fallback (the smoke CLI).

    Ignores the flag so the smoke test can also run with the bridge off;
    raises ``ImageBridgeConfigError`` when a URL is missing.
    """
    missing = missing_image_bridge_settings(settings)
    if missing:
        raise ImageBridgeConfigError(
            ERR_CONFIG_MISSING.format(names=CONFIG_NAMES_SEPARATOR.join(missing))
        )
    return GrokBotImageService(_waiter_deps(settings), _waiter_config(settings))


def build_callback_service() -> ImageBridgeCallbackService:
    """The callback use case over the shared Postgres session maker."""
    return ImageBridgeCallbackService(
        CallbackDeps(
            repository=SqlImageBridgeJobRepository(get_session_maker),
            codec=PillowImageCodec(),
            clock=SystemClock(),
        )
    )


def _waiter_deps(settings: Settings) -> GrokBotImageDeps:
    return GrokBotImageDeps(
        repository=SqlImageBridgeJobRepository(get_session_maker),
        webhook=HttpxGrokBotWebhook(
            WebhookClientConfig(
                url=settings.grokbot_image_webhook_url,
                auth_value=settings.grokbot_image_webhook_auth_value,
                auth_header=settings.grokbot_image_webhook_auth_header.strip(),
            )
        ),
        codec=PillowImageCodec(),
        clock=SystemClock(),
    )


def _waiter_config(settings: Settings) -> GrokBotImageConfig:
    return GrokBotImageConfig(
        callback_base_url=settings.image_bridge_public_base_url.strip(),
        timeout_seconds=settings.image_bridge_timeout_seconds,
        max_concurrency=settings.image_bridge_max_concurrency,
    )
