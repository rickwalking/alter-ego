"""Composition root of the image bridge module (AE-0393).

``build_carousel_openai_service`` is what the container hands to the image
provider registry as its OpenAI service: the plain OpenAI service when the
bridge is off (no behavior change), the Grok Bot bridge with the OpenAI
fallback when it is on.
"""

from __future__ import annotations

from rag_backend.domain.protocols import ImageGenerationService
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.config import get_session_maker
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


def validate_image_bridge_settings(settings: Settings) -> None:
    """Fail when the bridge is enabled without its URLs (any environment)."""
    if not settings.image_bridge_enabled:
        return
    missing = [
        name
        for name, value in (
            (ENV_WEBHOOK_URL, settings.grokbot_image_webhook_url.get_secret_value()),
            (ENV_PUBLIC_BASE_URL, settings.image_bridge_public_base_url),
        )
        if not value.strip()
    ]
    if missing:
        raise ImageBridgeConfigError(
            ERR_CONFIG_MISSING.format(names=CONFIG_NAMES_SEPARATOR.join(missing))
        )


def build_carousel_openai_service(
    settings: Settings, openai_service: ImageGenerationService
) -> ImageGenerationService:
    """The OpenAI-slot service for the registry, bridged when enabled."""
    if not settings.image_bridge_enabled:
        return openai_service
    validate_image_bridge_settings(settings)
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

    Validates the URLs as if the bridge were enabled, so the smoke test can
    run before the flag is flipped.
    """
    validate_image_bridge_settings(
        settings.model_copy(update={"image_bridge_enabled": True})
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
