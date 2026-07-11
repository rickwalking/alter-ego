"""Unit tests for the authenticated Redis client factory (AE-0302).

Gherkin: tests/features/redis_auth.feature —
  "missing credential fails fast", "unset or unrecognized ENVIRONMENT fails
  closed", "explicit development environment tolerates an absent password",
  "conflicting credentials fail closed", "the backend authenticates
  successfully" (URL construction + no-param-loss).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import SecretStr

from rag_backend.infrastructure.config.constants import (
    ENVIRONMENT_DEVELOPMENT,
    ENVIRONMENT_PRODUCTION,
    ENVIRONMENT_STAGING,
    ENVIRONMENT_TEST,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.events.redis_stream_publisher import (
    RedisStreamEventPublisher,
)
from rag_backend.infrastructure.redis_clients import (
    RedisConfigError,
    RedisConnectionConfig,
    create_redis_client,
    resolve_authed_redis_url,
)

_URL_BARE = "redis://redis:6379"
_URL_WITH_CREDS = "redis://:embedded-pw@redis:6379"
_URL_EMPTY_CREDS = "redis://:@redis:6379"
_PASSWORD = "managed-pw"
_ENVIRONMENT_UNRECOGNIZED = "prod"  # a typo'd value must fail closed


def _settings(
    *, environment: str, redis_url: str = _URL_BARE, password: str = ""
) -> Settings:
    return Settings(
        environment=environment,
        redis_url=redis_url,
        redis_password=SecretStr(password),
    )


# --- credential resolution policy -------------------------------------------


# Scenario: the backend authenticates successfully (URL construction)
def test_managed_password_is_injected_into_url() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION, password=_PASSWORD)

    assert resolve_authed_redis_url(settings) == f"redis://:{_PASSWORD}@redis:6379"


# Scenario: missing credential fails fast
def test_production_without_credential_raises() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION)

    with pytest.raises(RedisConfigError, match="REDIS_PASSWORD"):
        resolve_authed_redis_url(settings)


# Scenario: missing credential fails fast (empty URL fragment is NOT a credential)
def test_empty_url_credential_counts_as_missing_in_production() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION, redis_url=_URL_EMPTY_CREDS)

    with pytest.raises(RedisConfigError):
        resolve_authed_redis_url(settings)


# Scenario: unset or unrecognized ENVIRONMENT fails closed
@pytest.mark.parametrize(
    "environment", [_ENVIRONMENT_UNRECOGNIZED, ENVIRONMENT_STAGING, ""]
)
def test_unrecognized_environment_requires_auth(environment: str) -> None:
    settings = _settings(environment=environment)

    with pytest.raises(RedisConfigError):
        resolve_authed_redis_url(settings)


# Scenario: explicit development environment tolerates an absent password
@pytest.mark.parametrize("environment", [ENVIRONMENT_DEVELOPMENT, ENVIRONMENT_TEST])
def test_explicit_dev_test_allows_unauthenticated(environment: str) -> None:
    settings = _settings(environment=environment)

    assert resolve_authed_redis_url(settings) == _URL_BARE


# Scenario: conflicting credentials fail closed
def test_conflicting_url_and_managed_password_raise() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        redis_url=_URL_WITH_CREDS,
        password=_PASSWORD,
    )

    with pytest.raises(RedisConfigError, match="Refusing"):
        resolve_authed_redis_url(settings)


def test_matching_url_and_managed_password_accepted() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        redis_url="redis://:managed-pw@redis:6379",
        password=_PASSWORD,
    )

    assert resolve_authed_redis_url(settings) == "redis://:managed-pw@redis:6379"


def test_url_only_credential_is_accepted() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION, redis_url=_URL_WITH_CREDS)

    assert resolve_authed_redis_url(settings) == _URL_WITH_CREDS


# Scenario: conflicting credentials fail closed (query-param carrier, QA R1)
def test_conflicting_query_param_password_raises() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        redis_url="redis://redis:6379?password=stale-pw",
        password=_PASSWORD,
    )

    with pytest.raises(RedisConfigError, match="Refusing"):
        resolve_authed_redis_url(settings)


def test_query_param_credential_counts_as_present() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        redis_url="redis://redis:6379?password=qp-pw",
    )

    assert resolve_authed_redis_url(settings) == "redis://redis:6379?password=qp-pw"


# --- no param loss (AE-0302: per-consumer connection semantics) ---------------


def test_factory_forwards_consumer_connection_config() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION, password=_PASSWORD)
    config = RedisConnectionConfig(
        db=3,
        decode_responses=False,
        max_connections=7,
        socket_timeout=1.5,
        socket_connect_timeout=0.5,
    )

    with patch("redis.asyncio.Redis.from_url") as from_url:
        create_redis_client(settings, config)

    from_url.assert_called_once_with(
        f"redis://:{_PASSWORD}@redis:6379",
        db=3,
        decode_responses=False,
        max_connections=7,
        socket_timeout=1.5,
        socket_connect_timeout=0.5,
    )


def test_factory_defaults_preserve_streams_semantics() -> None:
    settings = _settings(environment=ENVIRONMENT_DEVELOPMENT)

    with patch("redis.asyncio.Redis.from_url") as from_url:
        create_redis_client(settings)

    kwargs = from_url.call_args.kwargs
    assert kwargs["decode_responses"] is True
    assert kwargs["db"] == 0


# --- the Streams publisher goes through the factory ---------------------------


# Scenario: the backend authenticates successfully (publisher path)
@pytest.mark.asyncio
async def test_stream_publisher_builds_client_via_factory() -> None:
    publisher = RedisStreamEventPublisher()
    sentinel = object()

    with patch(
        "rag_backend.infrastructure.events.redis_stream_publisher.create_redis_client",
        return_value=sentinel,
    ) as create:
        client = await publisher._get_client()

    assert client is sentinel
    config = create.call_args.args[1]
    assert config.decode_responses is True  # Streams consumer semantics preserved
