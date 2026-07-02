"""Startup guard tests for Redis credentials (AE-0302).

Separate file from test_startup_validation.py so the AE-0302 guard tests do
not entangle with the AE-0213/AE-0215 fixtures.

    Gherkin: tests/features/redis_auth.feature —
      "missing credential fails fast", "unset or unrecognized ENVIRONMENT
      fails closed", "explicit development environment tolerates an absent
      password".
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from rag_backend.bootstrap.startup_validation import (
    StartupValidationError,
    validate_redis_credentials,
)
from rag_backend.infrastructure.config.constants import (
    ENVIRONMENT_DEVELOPMENT,
    ENVIRONMENT_PRODUCTION,
)
from rag_backend.infrastructure.config.settings import Settings

_URL = "redis://redis:6379"
_PASSWORD = "startup-pw"


def _settings(*, environment: str, redis_url: str = _URL, password: str = "") -> Settings:
    return Settings(
        environment=environment,
        redis_url=redis_url,
        redis_password=SecretStr(password),
    )


# Scenario: missing credential fails fast (at startup, not first publish)
def test_production_redis_without_credential_fails_startup() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION)

    with pytest.raises(StartupValidationError, match="REDIS_PASSWORD"):
        validate_redis_credentials(settings)


# Scenario: unset or unrecognized ENVIRONMENT fails closed
def test_unrecognized_environment_fails_startup_without_credential() -> None:
    settings = _settings(environment="prd")

    with pytest.raises(StartupValidationError):
        validate_redis_credentials(settings)


def test_production_redis_with_credential_passes() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION, password=_PASSWORD)

    validate_redis_credentials(settings)  # does not raise


# Scenario: explicit development environment tolerates an absent password
def test_development_without_credential_passes() -> None:
    settings = _settings(environment=ENVIRONMENT_DEVELOPMENT)

    validate_redis_credentials(settings)  # does not raise


def test_no_redis_url_means_nothing_to_validate() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION, redis_url="")

    validate_redis_credentials(settings)  # memory publisher — does not raise
