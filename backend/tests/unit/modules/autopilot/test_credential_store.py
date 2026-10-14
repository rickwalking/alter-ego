"""Encrypted credential row, seed, and the publisher's token provider (AE-0358).

Gherkin: tests/features/autopilot_ig_token.feature
"""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
import structlog
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.application.credential_seed import (
    SeedCommand,
    seed_instagram_if_absent,
)
from rag_backend.modules.autopilot.bootstrap_credentials import (
    credential_tick_config,
    prepare_instagram_credentials,
)
from rag_backend.modules.autopilot.credential_constants import (
    KEY_PROBLEM_INVALID,
    KEY_PROBLEM_MISSING,
    LOG_CREDENTIALS_KEY_UNUSABLE,
    PROVIDER_INSTAGRAM,
    PUBLISHING_DISABLED,
    SEED_LIFETIME_DAYS,
)
from rag_backend.modules.autopilot.domain.token_refresh import seed_window
from rag_backend.modules.autopilot.infrastructure.credential_cipher import (
    FernetTokenCipher,
    encryption_key_problem,
    encryption_key_usable,
)
from rag_backend.modules.autopilot.infrastructure.credential_store import (
    SqlCredentialStore,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    IntegrationCredentialModel,
)
from rag_backend.modules.autopilot.infrastructure.stored_token_provider import (
    StoredInstagramTokenProvider,
    StoredTokenConfig,
    build_stored_instagram_token_provider,
)

_NOW = datetime(2026, 10, 14, 15, tzinfo=UTC)
_PLAIN = "plain token ! secret"


def _fernet_key() -> str:
    return Fernet.generate_key().decode()


def _capture(monkeypatch: pytest.MonkeyPatch, module_logger: str) -> io.StringIO:
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
    module = __import__(module_logger, fromlist=["logger"])
    monkeypatch.setattr(module, "logger", structlog.get_logger())
    return buffer


async def _ciphertext(session: AsyncSession) -> str:
    result = await session.execute(
        select(IntegrationCredentialModel.encrypted_token).where(
            IntegrationCredentialModel.provider == PROVIDER_INSTAGRAM
        )
    )
    stored = result.scalar_one()
    assert isinstance(stored, str)
    return stored


def _opener(session: AsyncSession):
    @asynccontextmanager
    async def _open() -> AsyncIterator[AsyncSession]:
        yield session

    return _open


@pytest.mark.asyncio
async def test_raw_row_is_not_plaintext_and_provider_returns_it(
    db_session: AsyncSession,
) -> None:
    """Scenario: Stored token is not plaintext."""
    key = _fernet_key()
    cipher = FernetTokenCipher(key)
    store = SqlCredentialStore(db_session, cipher)
    window = seed_window(_NOW)
    await seed_instagram_if_absent(SeedCommand(store=store, token=_PLAIN, now=_NOW))
    stored = await _ciphertext(db_session)
    assert _PLAIN not in stored
    provider = StoredInstagramTokenProvider(
        StoredTokenConfig(cipher=cipher, open_session=_opener(db_session))
    )
    assert await provider.get() == _PLAIN
    plain = await store.read(PROVIDER_INSTAGRAM)
    assert plain is not None
    assert plain.expires_at is not None
    assert plain.expires_at - window.expires_at == timedelta(0)


@pytest.mark.asyncio
async def test_seed_does_not_replace_an_existing_row(db_session: AsyncSession) -> None:
    """Scenario: Env token seeds the store once."""
    store = SqlCredentialStore(db_session, FernetTokenCipher(_fernet_key()))
    command = SeedCommand(store=store, token=_PLAIN, now=_NOW)
    assert await seed_instagram_if_absent(command)
    first = await _ciphertext(db_session)
    assert not await seed_instagram_if_absent(
        SeedCommand(store=store, token="other token ! secret", now=_NOW)
    )
    assert await _ciphertext(db_session) == first
    plain = await store.read(PROVIDER_INSTAGRAM)
    assert plain is not None
    assert plain.token == _PLAIN
    assert plain.expires_at == _NOW + timedelta(days=SEED_LIFETIME_DAYS)


@pytest.mark.asyncio
async def test_empty_store_returns_an_empty_token(db_session: AsyncSession) -> None:
    """Scenario: No token is configured."""
    provider = StoredInstagramTokenProvider(
        StoredTokenConfig(
            cipher=FernetTokenCipher(_fernet_key()),
            open_session=_opener(db_session),
        )
    )
    assert await provider.get() == ""


@pytest.mark.asyncio
async def test_database_not_ready_returns_an_empty_token() -> None:
    """Scenario: No token is configured."""

    def _closed() -> AsyncIterator[AsyncSession]:
        raise RuntimeError("database not initialized")

    provider = StoredInstagramTokenProvider(
        StoredTokenConfig(cipher=FernetTokenCipher(_fernet_key()), open_session=_closed)
    )
    assert await provider.get() == ""


@pytest.mark.asyncio
async def test_unreadable_ciphertext_is_absent(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    buffer = _capture(
        monkeypatch,
        "rag_backend.modules.autopilot.infrastructure.credential_store",
    )
    db_session.add(
        IntegrationCredentialModel(
            provider=PROVIDER_INSTAGRAM,
            encrypted_token="not-a-fernet-token",
            expires_at=_NOW,
            refreshed_at=_NOW,
        )
    )
    await db_session.flush()
    store = SqlCredentialStore(db_session, FernetTokenCipher(_fernet_key()))
    assert await store.read(PROVIDER_INSTAGRAM) is None
    assert _PLAIN not in buffer.getvalue()
    structlog.reset_defaults()


def test_missing_and_invalid_keys_are_not_usable() -> None:
    """Scenario: Encryption key missing disables publishing."""
    assert encryption_key_problem("") == KEY_PROBLEM_MISSING
    assert encryption_key_problem("not-a-fernet-key") == KEY_PROBLEM_INVALID
    assert not encryption_key_usable("")
    key = _fernet_key()
    assert encryption_key_usable(f"  {key}\n")
    assert isinstance(build_stored_instagram_token_provider(""), object)
    built = build_stored_instagram_token_provider("")
    assert built.__class__.__name__ == "EmptyInstagramTokenProvider"


@pytest.mark.asyncio
async def test_startup_warns_and_disables_publishing_without_a_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Encryption key missing disables publishing."""
    from rag_backend.bootstrap import autopilot_worker_factory
    from rag_backend.modules.autopilot import bootstrap_credentials

    buffer = _capture(
        monkeypatch, "rag_backend.modules.autopilot.bootstrap_credentials"
    )

    def _boom() -> None:
        raise AssertionError("database opened without a key")

    monkeypatch.setattr(bootstrap_credentials, "get_session_maker", _boom)
    settings = Settings(credentials_encryption_key="")
    await prepare_instagram_credentials(settings)
    rendered = buffer.getvalue()
    assert LOG_CREDENTIALS_KEY_UNUSABLE in rendered
    assert PUBLISHING_DISABLED in rendered
    assert credential_tick_config(settings) is None
    assert autopilot_worker_factory.instagram_publish_step(settings) is None
    assert autopilot_worker_factory.credential_refresh_step(settings) is None
    structlog.reset_defaults()


@pytest.mark.asyncio
async def test_startup_warning_does_not_include_an_invalid_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buffer = _capture(
        monkeypatch, "rag_backend.modules.autopilot.bootstrap_credentials"
    )
    secret = "not-a-fernet-key"
    await prepare_instagram_credentials(Settings(credentials_encryption_key=secret))
    assert secret not in buffer.getvalue()
    assert KEY_PROBLEM_INVALID in buffer.getvalue()
    structlog.reset_defaults()


@pytest.mark.asyncio
async def test_startup_seeds_once(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Env token seeds the store once."""
    from rag_backend.modules.autopilot import bootstrap_credentials

    key = _fernet_key()
    monkeypatch.setattr(
        bootstrap_credentials,
        "get_session_maker",
        lambda: _opener(db_session),
    )

    class _Clock:
        def now(self) -> datetime:
            return _NOW

    monkeypatch.setattr(bootstrap_credentials, "SystemClock", _Clock)
    settings = Settings(
        credentials_encryption_key=key,
        meta_ig_access_token=_PLAIN,
    )
    await prepare_instagram_credentials(settings)
    first = await _ciphertext(db_session)
    assert _PLAIN not in first
    await prepare_instagram_credentials(settings)
    assert await _ciphertext(db_session) == first
    plain = await SqlCredentialStore(db_session, FernetTokenCipher(key)).read(
        PROVIDER_INSTAGRAM
    )
    assert plain is not None
    assert plain.token == _PLAIN
    assert plain.expires_at == _NOW + timedelta(days=SEED_LIFETIME_DAYS)


@pytest.mark.asyncio
async def test_blank_env_token_does_not_open_the_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rag_backend.modules.autopilot import bootstrap_credentials

    def _boom() -> None:
        raise AssertionError("database opened without a token")

    monkeypatch.setattr(bootstrap_credentials, "get_session_maker", _boom)
    await prepare_instagram_credentials(
        Settings(credentials_encryption_key=_fernet_key(), meta_ig_access_token="  ")
    )


@pytest.mark.asyncio
async def test_seed_race_rolls_back(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import IntegrityError

    from rag_backend.modules.autopilot import bootstrap_credentials

    async def _race(_command: object) -> bool:
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr(
        bootstrap_credentials, "get_session_maker", lambda: _opener(db_session)
    )
    monkeypatch.setattr(bootstrap_credentials, "seed_instagram_if_absent", _race)
    await prepare_instagram_credentials(
        Settings(
            credentials_encryption_key=_fernet_key(),
            meta_ig_access_token=_PLAIN,
        )
    )
    result = await db_session.execute(
        select(IntegrationCredentialModel.provider).where(
            IntegrationCredentialModel.provider == PROVIDER_INSTAGRAM
        )
    )
    assert result.scalar_one_or_none() is None
