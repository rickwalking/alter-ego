"""Redis Streams event publisher (WF-001, ADR-004)."""

from __future__ import annotations

import json
from typing import cast

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.logging import get_logger
from rag_backend.infrastructure.redis_clients import (
    RedisConnectionConfig,
    create_redis_client,
)

logger = get_logger()

# Streams semantics: decoded responses; default pool/timeouts (XADD is
# non-blocking). AE-0302: built via the sanctioned factory so the client is
# authenticated; do not construct redis.Redis directly.
_STREAM_CLIENT_CONFIG = RedisConnectionConfig(decode_responses=True)


class RedisStreamEventPublisher:
    """Publishes domain events to Redis Streams."""

    def __init__(self) -> None:
        self._client: object | None = None

    async def _get_client(self) -> object:
        if self._client is not None:
            return self._client
        self._client = create_redis_client(get_settings(), _STREAM_CLIENT_CONFIG)
        return self._client

    async def publish(self, stream: str, event: dict[str, object]) -> str:
        client = await self._get_client()
        payload = json.dumps(event, default=str)
        entry_id = await cast(object, client).xadd(stream, {"data": payload})  # type: ignore[attr-defined]
        logger.info(
            "event_published",
            stream=stream,
            event_type=event.get("event_type"),
            aggregate_id=event.get("aggregate_id"),
        )
        return str(entry_id)

    async def close(self) -> None:
        if self._client is not None:
            await cast(object, self._client).close()  # type: ignore[attr-defined]
            self._client = None


__all__ = ["RedisStreamEventPublisher"]
