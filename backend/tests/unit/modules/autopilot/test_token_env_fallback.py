"""Manual publish keeps the legacy env token when the store cannot answer (QA r1 H6).

Gherkin: tests/features/autopilot_ig_token.feature
"""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import structlog
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.instagram_publisher_factory import (
    token_provider_for,
)
from rag_backend.modules.autopilot.bootstrap_credentials import (
    prepare_instagram_credentials,
)
from rag_backend.modules.autopilot.credential_constants import (
    FALLBACK_REASON_KEY_UNUSABLE,
    FALLBACK_REASON_STORE_EMPTY,
    FALLBACK_REASON_STORE_UNREADABLE,
    LOG_CREDENTIAL_ENV_FALLBACK,
    PUBLISHING_ENV_FALLBACK,
)
from rag_backend.modules.autopilot.infrastructure import stored_token_provider
from rag_backend.modules.autopilot.infrastructure.credential_cipher import (
    FernetTokenCipher,
)
from rag_backend.modules.autopilot.infrastructure.stored_token_provider import (
    EmptyInstagramTokenProvider,
    EnvInstagramTokenProvider,
    StoredInstagramTokenProvider,
    StoredTokenConfig,
    build_stored_instagram_token_provider,
)

_ENV_TOKEN = "env-legacy-token-secret"


def _capture(monkeypatch: pytest.MonkeyPatch, module: object) -> io.StringIO:
    buffer = io.StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(file=buffer),
        cache_logger_on_first_use=False,
    )
    monkeypatch.setattr(module, "logger", structlog.get_logger())
    return buffer


def _opener(session: AsyncSession):
    @asynccontextmanager
    async def _open() -> AsyncIterator[AsyncSession]:
        yield session

    return _open


# Scenario: Encryption key missing falls back to the env token
@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["", "not-a-fernet-key"])
async def test_unusable_key_returns_the_env_token(
    monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    """The manual route still gets the legacy token, with a warning."""
    buffer = _capture(monkeypatch, stored_token_provider)
    provider = build_stored_instagram_token_provider(key, f" {_ENV_TOKEN}\n")
    assert isinstance(provider, EnvInstagramTokenProvider)
    assert await provider.get() == _ENV_TOKEN
    rendered = buffer.getvalue()
    assert LOG_CREDENTIAL_ENV_FALLBACK in rendered
    assert FALLBACK_REASON_KEY_UNUSABLE in rendered
    assert _ENV_TOKEN not in rendered
    structlog.reset_defaults()


def test_unusable_key_without_env_token_stays_empty() -> None:
    """No key and no env token keeps the empty provider."""
    built = build_stored_instagram_token_provider("", "   ")
    assert isinstance(built, EmptyInstagramTokenProvider)


# Scenario: Encryption key missing falls back to the env token
@pytest.mark.asyncio
async def test_route_factory_passes_the_env_token() -> None:
    """``token_provider_for`` wires META_IG_ACCESS_TOKEN as the fallback."""
    settings = Settings(
        credentials_encryption_key="",
        meta_ig_access_token=_ENV_TOKEN,
    )
    assert await token_provider_for(settings).get() == _ENV_TOKEN


# Scenario: Stored token unreadable falls back to the env token
@pytest.mark.asyncio
async def test_empty_store_falls_back_to_env(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    buffer = _capture(monkeypatch, stored_token_provider)
    provider = StoredInstagramTokenProvider(
        StoredTokenConfig(
            cipher=FernetTokenCipher(Fernet.generate_key().decode()),
            open_session=_opener(db_session),
            fallback_token=_ENV_TOKEN,
        )
    )
    assert await provider.get() == _ENV_TOKEN
    assert FALLBACK_REASON_STORE_EMPTY in buffer.getvalue()
    assert _ENV_TOKEN not in buffer.getvalue()
    structlog.reset_defaults()


# Scenario: Stored token unreadable falls back to the env token
@pytest.mark.asyncio
async def test_unreadable_store_falls_back_to_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buffer = _capture(monkeypatch, stored_token_provider)

    def _closed() -> AsyncIterator[AsyncSession]:
        raise RuntimeError("database not initialized")

    provider = StoredInstagramTokenProvider(
        StoredTokenConfig(
            cipher=FernetTokenCipher(Fernet.generate_key().decode()),
            open_session=_closed,
            fallback_token=_ENV_TOKEN,
        )
    )
    assert await provider.get() == _ENV_TOKEN
    assert FALLBACK_REASON_STORE_UNREADABLE in buffer.getvalue()
    structlog.reset_defaults()


# Scenario: Encryption key missing falls back to the env token
@pytest.mark.asyncio
async def test_startup_reports_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from rag_backend.modules.autopilot import bootstrap_credentials

    buffer = _capture(monkeypatch, bootstrap_credentials)
    await prepare_instagram_credentials(
        Settings(credentials_encryption_key="", meta_ig_access_token=_ENV_TOKEN)
    )
    assert PUBLISHING_ENV_FALLBACK in buffer.getvalue()
    assert _ENV_TOKEN not in buffer.getvalue()
    structlog.reset_defaults()
