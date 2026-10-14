"""``InstagramTokenProvider`` backed by the encrypted credential row."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.autopilot.credential_constants import (
    FALLBACK_REASON_KEY_UNUSABLE,
    FALLBACK_REASON_STORE_EMPTY,
    FALLBACK_REASON_STORE_UNREADABLE,
    LOG_CREDENTIAL_ENV_FALLBACK,
    LOG_CREDENTIAL_READ_FAILED,
    PROVIDER_INSTAGRAM,
)
from rag_backend.modules.autopilot.domain.credential_ports import PlainCredential
from rag_backend.modules.autopilot.infrastructure.credential_cipher import (
    FernetTokenCipher,
    encryption_key_usable,
)
from rag_backend.modules.autopilot.infrastructure.credential_store import (
    SqlCredentialStore,
)

logger = structlog.get_logger()

SessionOpener = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True, kw_only=True)
class StoredTokenConfig:
    """Cipher plus a session opener. ``get`` does not commit.

    ``fallback_token`` is the legacy ``META_IG_ACCESS_TOKEN``. It is used
    when the store cannot answer, so manual publishing keeps working.
    """

    cipher: FernetTokenCipher
    open_session: SessionOpener
    fallback_token: str = ""


class EmptyInstagramTokenProvider:
    """No usable Fernet key, so the publish job fails fast."""

    def __init__(self) -> None:
        self._empty = ""

    async def get(self) -> str:
        """Return an empty token."""
        return self._empty


class EnvInstagramTokenProvider:
    """Legacy env token. Used when the Fernet key is unusable (QA r1 H6)."""

    def __init__(self, token: str) -> None:
        self._token = token

    async def get(self) -> str:
        """Return the env token and warn that the store was bypassed."""
        return fallback_token(self._token, FALLBACK_REASON_KEY_UNUSABLE)


class StoredInstagramTokenProvider:
    """Decrypts ``provider=instagram`` on each ``get``."""

    def __init__(self, config: StoredTokenConfig) -> None:
        self._config = config

    async def get(self) -> str:
        """Return the plaintext token, or ``""`` when none is stored."""
        fallback = self._config.fallback_token
        try:
            plain = await self._read()
        except RuntimeError:
            logger.warning(LOG_CREDENTIAL_READ_FAILED, provider=PROVIDER_INSTAGRAM)
            return fallback_token(fallback, FALLBACK_REASON_STORE_UNREADABLE)
        if plain is None or not plain.token:
            return fallback_token(fallback, FALLBACK_REASON_STORE_EMPTY)
        return plain.token

    async def _read(self) -> PlainCredential | None:
        async with self._config.open_session() as session:
            store = SqlCredentialStore(session, self._config.cipher)
            return await store.read(PROVIDER_INSTAGRAM)


TokenProvider = (
    EmptyInstagramTokenProvider
    | EnvInstagramTokenProvider
    | StoredInstagramTokenProvider
)


def build_stored_instagram_token_provider(
    encryption_key: str,
    env_token: str = "",
) -> TokenProvider:
    """Store-backed provider. Without a usable key, the env token or nothing."""
    if not encryption_key_usable(encryption_key):
        return _keyless(env_token)
    config = StoredTokenConfig(
        cipher=FernetTokenCipher(encryption_key),
        open_session=_open_session,
        fallback_token=env_token.strip(),
    )
    return StoredInstagramTokenProvider(config)


def fallback_token(token: str, reason: str) -> str:
    """Return ``token``. Warns (without the token) when it is non-empty."""
    if token:
        logger.warning(
            LOG_CREDENTIAL_ENV_FALLBACK,
            provider=PROVIDER_INSTAGRAM,
            reason=reason,
        )
    return token


def _keyless(env_token: str) -> EmptyInstagramTokenProvider | EnvInstagramTokenProvider:
    token = env_token.strip()
    if not token:
        return EmptyInstagramTokenProvider()
    return EnvInstagramTokenProvider(token)


def _open_session() -> AbstractAsyncContextManager[AsyncSession]:
    return get_session_maker()()
