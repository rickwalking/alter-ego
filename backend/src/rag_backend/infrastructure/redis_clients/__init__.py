"""Authenticated Redis client construction (AE-0302). Facade for the package."""

from rag_backend.infrastructure.redis_clients.factory import (
    RedisConfigError,
    RedisConnectionConfig,
    create_redis_client,
    resolve_authed_redis_url,
)

__all__ = [
    "RedisConfigError",
    "RedisConnectionConfig",
    "create_redis_client",
    "resolve_authed_redis_url",
]
