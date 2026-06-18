"""Unit tests for composition-root startup hardening.

Covers tests/features/startup_hardening.feature:
* AE-0213 — durable LangGraph checkpointer guard.
* AE-0215 — default image-provider key guard.

The guards read only ``Settings`` and either raise (production-like) or warn
(dev/test). Tests build prod-like and dev-like settings objects directly.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from rag_backend.bootstrap.startup_validation import (
    StartupValidationError,
    run_startup_validations,
    validate_checkpointer_durability,
    validate_default_image_provider_key,
)
from rag_backend.infrastructure.config.constants import (
    ENVIRONMENT_DEVELOPMENT,
    ENVIRONMENT_PRODUCTION,
)
from rag_backend.infrastructure.config.settings import Settings

_CHECKPOINT_BACKEND_MEMORY = "memory"
_CHECKPOINT_BACKEND_DISABLED = "disabled"
_CHECKPOINT_BACKEND_POSTGRES = "postgres"
_DEFAULT_PROVIDER_KEY = "openai-test-key"  # default provider (IMAGE_MODEL_DEFAULT=openai)


def _settings(
    *,
    environment: str,
    checkpoint_backend: str = _CHECKPOINT_BACKEND_POSTGRES,
    default_provider_key: str = _DEFAULT_PROVIDER_KEY,
) -> Settings:
    """Build a Settings object for the given environment.

    ``secret_key`` / ``anon_secret_key`` come from the test env (conftest), so
    they are not passed explicitly here.
    """
    return Settings(
        environment=environment,
        carousel_checkpoint_backend=checkpoint_backend,
        openai_api_key=SecretStr(default_provider_key),
    )


# --- AE-0213: durable checkpointer ------------------------------------------


# Scenario: Production rejects a non-durable (memory) checkpointer
def test_prod_memory_checkpointer_raises() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        checkpoint_backend=_CHECKPOINT_BACKEND_MEMORY,
    )
    with pytest.raises(StartupValidationError):
        validate_checkpointer_durability(settings)


# Scenario: Production rejects a disabled checkpointer
def test_prod_disabled_checkpointer_raises() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        checkpoint_backend=_CHECKPOINT_BACKEND_DISABLED,
    )
    with pytest.raises(StartupValidationError):
        validate_checkpointer_durability(settings)


# Scenario: Production accepts a postgres checkpointer
def test_prod_postgres_checkpointer_passes() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        checkpoint_backend=_CHECKPOINT_BACKEND_POSTGRES,
    )
    assert validate_checkpointer_durability(settings) is True


# Scenario: Development tolerates a non-durable checkpointer with a warning
def test_dev_memory_checkpointer_warns_not_raises() -> None:
    settings = _settings(
        environment=ENVIRONMENT_DEVELOPMENT,
        checkpoint_backend=_CHECKPOINT_BACKEND_MEMORY,
    )
    assert validate_checkpointer_durability(settings) is False


def test_staging_is_production_like_for_checkpointer() -> None:
    """Staging (not in NON_PRODUCTION_ENVIRONMENTS) must also fail fast."""
    settings = _settings(
        environment="staging",
        checkpoint_backend=_CHECKPOINT_BACKEND_MEMORY,
    )
    with pytest.raises(StartupValidationError):
        validate_checkpointer_durability(settings)


# --- AE-0215: default image-provider key ------------------------------------


# Scenario: Production rejects a missing default image-provider key
def test_prod_missing_default_image_key_raises() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION, default_provider_key="")
    with pytest.raises(StartupValidationError):
        validate_default_image_provider_key(settings)


# Scenario: Production accepts a present default image-provider key
def test_prod_present_default_image_key_passes() -> None:
    settings = _settings(environment=ENVIRONMENT_PRODUCTION, default_provider_key=_DEFAULT_PROVIDER_KEY)
    assert validate_default_image_provider_key(settings) is True


# Scenario: Development tolerates a missing default image-provider key
def test_dev_missing_default_image_key_warns_not_raises() -> None:
    settings = _settings(environment=ENVIRONMENT_DEVELOPMENT, default_provider_key="")
    assert validate_default_image_provider_key(settings) is False


# --- combined entry point ---------------------------------------------------


def test_run_startup_validations_prod_all_good() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        checkpoint_backend=_CHECKPOINT_BACKEND_POSTGRES,
        default_provider_key=_DEFAULT_PROVIDER_KEY,
    )
    result = run_startup_validations(settings)
    assert result.checkpoint_durable is True
    assert result.default_image_provider_usable is True


def test_run_startup_validations_prod_memory_backend_raises() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        checkpoint_backend=_CHECKPOINT_BACKEND_MEMORY,
        default_provider_key=_DEFAULT_PROVIDER_KEY,
    )
    with pytest.raises(StartupValidationError):
        run_startup_validations(settings)


def test_run_startup_validations_prod_missing_image_key_raises() -> None:
    settings = _settings(
        environment=ENVIRONMENT_PRODUCTION,
        checkpoint_backend=_CHECKPOINT_BACKEND_POSTGRES,
        default_provider_key="",
    )
    with pytest.raises(StartupValidationError):
        run_startup_validations(settings)


def test_run_startup_validations_dev_degraded_reports_flags() -> None:
    settings = _settings(
        environment=ENVIRONMENT_DEVELOPMENT,
        checkpoint_backend=_CHECKPOINT_BACKEND_MEMORY,
        default_provider_key="",
    )
    result = run_startup_validations(settings)
    assert result.checkpoint_durable is False
    assert result.default_image_provider_usable is False
