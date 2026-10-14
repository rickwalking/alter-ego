"""``InstagramTokenProvider`` backed by the encrypted credential row."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.autopilot.credential_constants import (
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
    """Cipher plus a session opener. ``get`` does not commit."""

    cipher: FernetTokenCipher
    open_session: SessionOpener


class EmptyInstagramTokenProvider:
    """No usable Fernet key, so the publish job fails fast."""

    def __init__(self) -> None:
        self._empty = ""

    async def get(self) -> str:
        """Return an empty token."""
        return self._empty


class StoredInstagramTokenProvider:
    """Decrypts ``provider=instagram`` on each ``get``."""

    def __init__(self, config: StoredTokenConfig) -> None:
        self._config = config

    async def get(self) -> str:
        """Return the plaintext token, or ``""`` when none is stored."""
        try:
            plain = await self._read()
        except RuntimeError:
            logger.warning(LOG_CREDENTIAL_READ_FAILED, provider=PROVIDER_INSTAGRAM)
            return ""
        if plain is None or not plain.token:
            return ""
        return plain.token

    async def _read(self) -> PlainCredential | None:
        async with self._config.open_session() as session:
            store = SqlCredentialStore(session, self._config.cipher)
            return await store.read(PROVIDER_INSTAGRAM)


def build_stored_instagram_token_provider(
    encryption_key: str,
) -> EmptyInstagramTokenProvider | StoredInstagramTokenProvider:
    """Store-backed provider, or an empty one when the Fernet key is unusable."""
    if not encryption_key_usable(encryption_key):
        return EmptyInstagramTokenProvider()
    config = StoredTokenConfig(
        cipher=FernetTokenCipher(encryption_key),
        open_session=_open_session,
    )
    return StoredInstagramTokenProvider(config)


def _open_session() -> AbstractAsyncContextManager[AsyncSession]:
    return get_session_maker()()
