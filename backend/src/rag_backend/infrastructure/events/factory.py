"""Factory for event publisher selection."""

from __future__ import annotations

from rag_backend.domain.protocols.event_publisher import EventPublisherProtocol
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
)
from rag_backend.infrastructure.events.redis_stream_publisher import (
    RedisStreamEventPublisher,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_publisher: EventPublisherProtocol | None = None


def get_event_publisher(redis_url: str | None) -> EventPublisherProtocol:
    """Return Redis publisher when configured, otherwise in-memory fallback."""
    global _publisher
    if _publisher is not None:
        return _publisher
    if redis_url:
        try:
            _publisher = RedisStreamEventPublisher()
        except Exception:
            logger.warning("event_publisher_redis_failed", hint="using memory fallback")
        else:
            logger.info("event_publisher_redis", url=redis_url.split("@")[-1])
            return _publisher
    else:
        logger.info("event_publisher_memory", hint="redis not configured")
    _publisher = MemoryEventPublisher()
    return _publisher


def reset_event_publisher() -> None:
    """Reset singleton (tests)."""
    global _publisher
    _publisher = None


__all__ = ["get_event_publisher", "reset_event_publisher"]
