"""Startup hardening validations for the composition root.

These guards run during application startup (``lifespan``) and assert that a
production-like deployment is configured durably and completely:

* AE-0213 — the LangGraph carousel checkpointer uses a durable backend
  (not the in-memory saver) so workflow state survives restarts.
* AE-0215 — the *default* carousel image provider has a usable API key, so a
  default-preset carousel does not fail late at image-generation time.

The checks live here (and not in ``application``/``api``) deliberately: they are
infrastructure-aware composition-root concerns. They read only ``Settings`` and
emit a structured log; production-like environments fail fast, dev/test do not.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.domain.constants import IMAGE_MODEL_DEFAULT
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.logging import get_logger
from rag_backend.infrastructure.redis_clients import (
    RedisConfigError,
    resolve_authed_redis_url,
)

logger = get_logger()

# --- AE-0213: durable checkpointer -----------------------------------------

# Non-durable carousel checkpoint backends: state does not survive a restart.
NON_DURABLE_CHECKPOINT_BACKENDS: frozenset[str] = frozenset({"memory", "disabled"})

EVENT_CHECKPOINT_NON_DURABLE = "startup_checkpoint_backend_non_durable"
HINT_CHECKPOINT_DURABLE = (
    "set CAROUSEL_CHECKPOINT_BACKEND=postgres and "
    "CAROUSEL_CHECKPOINT_POSTGRES_URL for durable workflow state"
)
_ERR_CHECKPOINT_NON_DURABLE = (
    "Non-durable carousel checkpoint backend {backend!r} is not allowed in a "
    "production-like environment ({environment!r}). " + HINT_CHECKPOINT_DURABLE
)

# --- AE-0215: default image-provider key ------------------------------------

EVENT_IMAGE_PROVIDER_KEY_MISSING = "startup_default_image_provider_key_missing"
HINT_IMAGE_PROVIDER_KEY = (
    "set the API key for the default image provider "
    "(IMAGE_MODEL_DEFAULT) or change the default preset to a configured provider"
)
_ERR_IMAGE_PROVIDER_KEY_MISSING = (
    "Default image provider {provider!r} has no API key configured; a "
    "default-preset carousel would fail at image generation in a "
    "production-like environment ({environment!r}). " + HINT_IMAGE_PROVIDER_KEY
)
_ERR_UNKNOWN_DEFAULT_PROVIDER = (
    "Default image provider {provider!r} has no known API-key mapping; cannot "
    "validate its credentials at startup."
)


class StartupValidationError(RuntimeError):
    """Raised when a production-like deployment is misconfigured at startup."""


@dataclass(frozen=True)
class StartupValidationResult:
    """Outcome of a non-fatal startup guard run in dev/test.

    ``checkpoint_durable`` / ``default_image_provider_usable`` are ``False`` when
    the corresponding guard found a problem that was downgraded to a warning
    because the environment is not production-like.
    """

    checkpoint_durable: bool
    default_image_provider_usable: bool


def _provider_key_present(settings: Settings, provider: str) -> bool:
    """Return whether the API key for ``provider`` is configured (non-empty).

    Delegates to ``Settings.image_provider_api_key`` — the single provider→key
    mapping shared with the AE-0308 request-time creation guard. An unmapped
    provider raises rather than silently passing the guard.
    """
    key = settings.image_provider_api_key(provider)
    if key is None:
        raise StartupValidationError(
            _ERR_UNKNOWN_DEFAULT_PROVIDER.format(provider=provider)
        )
    return bool(key.get_secret_value())


def validate_checkpointer_durability(settings: Settings) -> bool:
    """AE-0213: guard against a non-durable checkpointer in production.

    Returns ``True`` when the backend is durable (or the environment tolerates a
    non-durable one). Raises :class:`StartupValidationError` for a non-durable
    backend in a production-like environment; warns (and returns ``False``) in
    dev/test.
    """
    backend = settings.carousel_checkpoint_backend.strip().lower()
    if backend not in NON_DURABLE_CHECKPOINT_BACKENDS:
        return True

    if settings.is_production_like:
        raise StartupValidationError(
            _ERR_CHECKPOINT_NON_DURABLE.format(
                backend=backend, environment=settings.environment
            )
        )

    logger.warning(
        EVENT_CHECKPOINT_NON_DURABLE,
        backend=backend,
        environment=settings.environment,
        hint=HINT_CHECKPOINT_DURABLE,
    )
    return False


def validate_default_image_provider_key(settings: Settings) -> bool:
    """AE-0215: guard that the default image provider's key is usable.

    Returns ``True`` when the default provider's key is present (or the
    environment tolerates its absence). Raises :class:`StartupValidationError`
    when the key is missing in a production-like environment; warns (and returns
    ``False``) in dev/test so the default preset is treated as disabled.
    """
    provider = IMAGE_MODEL_DEFAULT
    if _provider_key_present(settings, provider):
        return True

    if settings.is_production_like:
        raise StartupValidationError(
            _ERR_IMAGE_PROVIDER_KEY_MISSING.format(
                provider=provider, environment=settings.environment
            )
        )

    logger.warning(
        EVENT_IMAGE_PROVIDER_KEY_MISSING,
        provider=provider,
        environment=settings.environment,
        hint=HINT_IMAGE_PROVIDER_KEY,
    )
    return False


def validate_redis_credentials(settings: Settings) -> None:
    """AE-0302: fail fast when Redis is configured without a credential.

    Delegates the policy to the sanctioned client factory
    (``redis_clients.resolve_authed_redis_url``): missing/empty credentials in a
    production-like environment — including an unset or unrecognized
    ``ENVIRONMENT`` — raise; explicit dev/test tolerates an unauthenticated
    local Redis (the factory logs a warning). An empty ``REDIS_URL`` means the
    in-memory event publisher is in use, so there is nothing to validate.
    """
    if not settings.redis_url:
        return
    try:
        resolve_authed_redis_url(settings)
    except RedisConfigError as exc:
        raise StartupValidationError(str(exc)) from exc


def run_startup_validations(settings: Settings) -> StartupValidationResult:
    """Run all composition-root startup guards.

    Raises :class:`StartupValidationError` on the first fatal misconfiguration in
    a production-like environment. In dev/test, downgrades to warnings and
    reports which guards flagged a problem.
    """
    validate_redis_credentials(settings)
    return StartupValidationResult(
        checkpoint_durable=validate_checkpointer_durability(settings),
        default_image_provider_usable=validate_default_image_provider_key(settings),
    )
