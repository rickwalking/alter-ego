"""Persist Instagram tokens as Fernet ciphertext. Reads never return the column raw."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.credential_constants import (
    LOG_CREDENTIAL_DECRYPT_FAILED,
)
from rag_backend.modules.autopilot.domain.credential_ports import (
    PlainCredential,
    WriteCredential,
)
from rag_backend.modules.autopilot.infrastructure.credential_cipher import (
    CredentialDecryptError,
    FernetTokenCipher,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    IntegrationCredentialModel,
)

logger = structlog.get_logger()


class SqlCredentialStore:
    """One session's view of ``integration_credentials``."""

    def __init__(self, session: AsyncSession, cipher: FernetTokenCipher) -> None:
        self._session = session
        self._cipher = cipher

    async def exists(self, provider: str) -> bool:
        """True when the provider row is present. Does not decrypt."""
        row = await self._session.get(IntegrationCredentialModel, provider)
        return row is not None

    async def read(self, provider: str) -> PlainCredential | None:
        """Decrypt the row. Unreadable ciphertext is treated as absent."""
        row = await self._session.get(IntegrationCredentialModel, provider)
        if row is None:
            return None
        token = self._plaintext(row.encrypted_token, provider)
        if token is None:
            return None
        return PlainCredential(
            provider=row.provider,
            token=token,
            expires_at=_aware(row.expires_at),
            refreshed_at=_aware(row.refreshed_at),
        )

    async def write(self, command: WriteCredential) -> None:
        """Replace the row's ciphertext. The caller commits."""
        ciphertext = self._cipher.encrypt(command.token)
        row = await self._session.get(IntegrationCredentialModel, command.provider)
        if row is None:
            self._session.add(_row(command, ciphertext))
        else:
            _fill(row, command, ciphertext)
        await self._session.flush()

    def _plaintext(self, ciphertext: str, provider: str) -> str | None:
        try:
            return self._cipher.decrypt(ciphertext)
        except CredentialDecryptError:
            logger.warning(LOG_CREDENTIAL_DECRYPT_FAILED, provider=provider)
            return None


def _row(command: WriteCredential, ciphertext: str) -> IntegrationCredentialModel:
    return IntegrationCredentialModel(
        provider=command.provider,
        encrypted_token=ciphertext,
        expires_at=command.expires_at,
        refreshed_at=command.refreshed_at,
    )


def _fill(
    row: IntegrationCredentialModel, command: WriteCredential, ciphertext: str
) -> None:
    row.encrypted_token = ciphertext
    row.expires_at = command.expires_at
    row.refreshed_at = command.refreshed_at


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
