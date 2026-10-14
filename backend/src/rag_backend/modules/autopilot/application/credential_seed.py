"""Insert the env Instagram token once. An existing row is left alone."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rag_backend.modules.autopilot.credential_constants import PROVIDER_INSTAGRAM
from rag_backend.modules.autopilot.domain.credential_ports import (
    CredentialStore,
    WriteCredential,
)
from rag_backend.modules.autopilot.domain.token_refresh import seed_window


@dataclass(frozen=True, kw_only=True)
class SeedCommand:
    """Env token plus the clock used for the conservative 60-day expiry."""

    store: CredentialStore
    token: str
    now: datetime


async def seed_instagram_if_absent(command: SeedCommand) -> bool:
    """Insert ``command.token`` when the instagram row is missing."""
    if not command.token.strip():
        return False
    if await command.store.exists(PROVIDER_INSTAGRAM):
        return False
    window = seed_window(command.now)
    await command.store.write(
        WriteCredential(
            provider=PROVIDER_INSTAGRAM,
            token=command.token,
            expires_at=window.expires_at,
            refreshed_at=window.refreshed_at,
        )
    )
    return True
