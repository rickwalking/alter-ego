"""Primary image service with an OpenAI fallback (ADR-0022).

Any exception from the primary (the Grok Bot bridge) runs the fallback
(``OpenAIImageService``) when the fallback is enabled; otherwise the
primary's error propagates unchanged. Each image logs which provider made it.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.domain.protocols import ImageGenerationService
from rag_backend.modules.image_bridge.constants import (
    LOG_FALLBACK,
    LOG_IMAGE_GENERATED,
    PROVIDER_GROKBOT,
    PROVIDER_OPENAI_FALLBACK,
    REASON_FORMAT,
    REASON_MAX_CHARS,
)

logger = structlog.get_logger()


@dataclass(frozen=True)
class FallbackImageConfig:
    """The two services and whether the fallback may run."""

    primary: ImageGenerationService
    fallback: ImageGenerationService
    fallback_enabled: bool


class FallbackImageService(ImageGenerationService):
    """Tries the primary; on failure, the fallback when enabled."""

    def __init__(self, config: FallbackImageConfig) -> None:
        self._config = config

    async def generate_image(self, prompt: str, output_path: str) -> str:
        """Generate with the primary, falling back on any exception."""
        try:
            result = await self._config.primary.generate_image(prompt, output_path)
        except Exception as exc:
            if not self._config.fallback_enabled:
                raise
            logger.warning(
                LOG_FALLBACK,
                image_provider=PROVIDER_OPENAI_FALLBACK,
                reason=failure_reason(exc),
            )
            result = await self._config.fallback.generate_image(prompt, output_path)
            logger.info(LOG_IMAGE_GENERATED, image_provider=PROVIDER_OPENAI_FALLBACK)
            return result
        logger.info(LOG_IMAGE_GENERATED, image_provider=PROVIDER_GROKBOT)
        return result


def failure_reason(exc: BaseException) -> str:
    """Short, log-safe reason: the exception type and a bounded message."""
    reason = REASON_FORMAT.format(kind=type(exc).__name__, message=exc)
    return reason[:REASON_MAX_CHARS]
