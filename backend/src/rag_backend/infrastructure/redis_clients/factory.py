"""Single sanctioned Redis client factory (AE-0302).

Every backend Redis client is built here — and only here. Direct
``redis.Redis(...)`` / ``Redis.from_url(...)`` construction outside this module
is prohibited and enforced by ``scripts/check_redis_factory.py`` (a rule-fires
checked gate), so a future consumer cannot silently bypass the authenticated
path.

Credential policy (fails closed):

* ``REDIS_PASSWORD`` is the managed credential; a password embedded in
  ``REDIS_URL`` that is absent or empty counts as *missing*.
* If both are set and disagree, raise — a stale ``REDIS_URL`` must not be able
  to override the managed password.
* In a production-like environment (``production``, ``staging``, unset, or any
  unrecognized value — see ``Settings.is_production_like``) a missing
  credential raises :class:`RedisConfigError`; only explicit dev/test relaxes
  it (local/CI still run unauthenticated).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.logging import get_logger
from rag_backend.infrastructure.redis_clients.constants import (
    ERR_CONFLICTING_CREDENTIALS,
    ERR_MISSING_CREDENTIAL,
    EVENT_REDIS_UNAUTHENTICATED_DEV,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from redis.asyncio import Redis

logger = get_logger()


class RedisConfigError(RuntimeError):
    """Raised when Redis credentials are missing or conflicting."""


@dataclass(frozen=True)
class RedisConnectionConfig:
    """Per-consumer connection semantics the factory must preserve.

    A blocking Streams reader and a cache have different needs (AE-0302:
    "no param loss") — the factory forwards these verbatim instead of
    flattening every consumer onto one connection profile.
    """

    db: int = 0
    decode_responses: bool = True
    max_connections: int | None = None
    socket_timeout: float | None = None
    socket_connect_timeout: float | None = None


def _url_password(url: str) -> str | None:
    """Return the password embedded in ``url``, treating empty as absent."""
    try:
        password = urlsplit(url).password
    except ValueError:
        return None
    return password or None


def _with_password(url: str, password: str) -> str:
    """Return ``url`` with ``password`` injected (username preserved)."""
    parts = urlsplit(url)
    username = parts.username or ""
    host = parts.hostname or ""
    netloc = f"{username}:{password}@{host}"
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def resolve_authed_redis_url(settings: Settings) -> str:
    """Resolve the effective Redis URL, enforcing the credential policy."""
    url = settings.redis_url
    url_password = _url_password(url)
    managed_password = settings.redis_password.get_secret_value() or None

    if url_password and managed_password and url_password != managed_password:
        raise RedisConfigError(ERR_CONFLICTING_CREDENTIALS)
    if managed_password and managed_password != url_password:
        return _with_password(url, managed_password)
    if url_password:
        return url

    if settings.is_production_like:
        raise RedisConfigError(
            ERR_MISSING_CREDENTIAL.format(environment=settings.environment)
        )
    logger.warning(EVENT_REDIS_UNAUTHENTICATED_DEV, environment=settings.environment)
    return url


def create_redis_client(
    settings: Settings, config: RedisConnectionConfig | None = None
) -> Redis:
    """Build the authenticated async Redis client (the ONLY construction site)."""
    from redis.asyncio import Redis

    effective = config or RedisConnectionConfig()
    return Redis.from_url(
        resolve_authed_redis_url(settings),
        db=effective.db,
        decode_responses=effective.decode_responses,
        max_connections=effective.max_connections,
        socket_timeout=effective.socket_timeout,
        socket_connect_timeout=effective.socket_connect_timeout,
    )


__all__ = [
    "RedisConfigError",
    "RedisConnectionConfig",
    "create_redis_client",
    "resolve_authed_redis_url",
]
