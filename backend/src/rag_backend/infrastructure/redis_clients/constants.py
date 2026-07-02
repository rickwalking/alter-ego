"""Constants for the authenticated Redis client factory (AE-0302)."""

from __future__ import annotations

ERR_MISSING_CREDENTIAL = (
    "Redis credentials are required in a production-like environment "
    "({environment!r}) but neither REDIS_PASSWORD nor a password embedded in "
    "REDIS_URL is set. Set the REDIS_PASSWORD secret (see .env.example)."
)
ERR_CONFLICTING_CREDENTIALS = (
    "REDIS_URL embeds a password that differs from REDIS_PASSWORD. Refusing to "
    "pick one silently: remove the credential from REDIS_URL and manage it via "
    "REDIS_PASSWORD only."
)

EVENT_REDIS_UNAUTHENTICATED_DEV = "redis_client_unauthenticated_dev"

__all__ = [
    "ERR_CONFLICTING_CREDENTIALS",
    "ERR_MISSING_CREDENTIAL",
    "EVENT_REDIS_UNAUTHENTICATED_DEV",
]
