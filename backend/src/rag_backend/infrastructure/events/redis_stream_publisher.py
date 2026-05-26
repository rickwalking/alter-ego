"""Redis Streams event publisher (WF-001, ADR-004)."""

from __future__ import annotations

import json
from typing import cast

from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


class RedisStreamEventPublisher:
    """Publishes domain events to Redis Streams."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: object | None = None

    async def _get_client(self) -> object:
        if self._client is not None:
            return self._client
        from redis.asyncio import Redis

        self._client = Redis.from_url(self._redis_url, decode_responses=True)
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
