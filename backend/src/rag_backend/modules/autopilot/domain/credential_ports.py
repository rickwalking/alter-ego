"""Ports for the encrypted Instagram token. Plaintext stays in memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from rag_backend.modules.autopilot.credential_constants import REFRESH_FAILED_MESSAGE


@dataclass(frozen=True, kw_only=True)
class PlainCredential:
    """Decrypted token plus the clocks the refresher compares."""

    provider: str
    token: str
    expires_at: datetime | None
    refreshed_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class WriteCredential:
    """Plaintext to encrypt and store. Callers do not pass ciphertext."""

    provider: str
    token: str
    expires_at: datetime
    refreshed_at: datetime


@dataclass(frozen=True, kw_only=True)
class RefreshRequest:
    """One refresh. The token is the query secret and must not be logged."""

    token: str


@dataclass(frozen=True, kw_only=True)
class RefreshGrant:
    """A successful ``refresh_access_token`` body, without ``token_type``."""

    access_token: str
    expires_in: int


class TokenRefreshError(Exception):
    """Graph refused the refresh. The message does not include the token."""

    def __init__(self, status_code: int, error_code: int | None) -> None:
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(REFRESH_FAILED_MESSAGE)


class CredentialStore(Protocol):
    """Encrypted ``integration_credentials`` rows for one session."""

    async def exists(self, provider: str) -> bool:
        """True when a row is stored. Does not decrypt."""
        ...

    async def read(self, provider: str) -> PlainCredential | None:
        """Decrypt the row, or None when it is missing or unreadable."""
        ...

    async def write(self, command: WriteCredential) -> None:
        """Insert or replace the ciphertext. The caller commits."""
        ...


class TokenRefreshClient(Protocol):
    """Instagram long-lived token refresh."""

    async def refresh(self, request: RefreshRequest) -> RefreshGrant:
        """Exchange the current token. Raises ``TokenRefreshError`` on failure."""
        ...


class TokenAlerter(Protocol):
    """Sends one owner alert. Delivery failures stay inside the adapter."""

    async def send(self, message: str) -> None:
        """Deliver ``message``. The message must not contain the token."""
        ...


class RefreshDayGate(Protocol):
    """Lets the credential step run once per local calendar day."""

    def claim(self, now: datetime) -> bool:
        """True the first time ``now`` falls on a new local day."""
        ...
