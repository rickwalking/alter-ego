"""Daily Instagram token refresh. At most one Graph call per local day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import structlog

from rag_backend.modules.autopilot.credential_constants import (
    LOG_CREDENTIAL_REFRESH_FAILED,
    LOG_CREDENTIAL_REFRESHED,
    PROVIDER_INSTAGRAM,
)
from rag_backend.modules.autopilot.domain.credential_ports import (
    CredentialStore,
    PlainCredential,
    RefreshDayGate,
    RefreshGrant,
    RefreshRequest,
    TokenAlerter,
    TokenRefreshClient,
    TokenRefreshError,
    WriteCredential,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.token_refresh import (
    AlertFacts,
    alert_message,
    expiry_after_grant,
    refresh_due,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class TokenRefresherDependencies:
    """Ports for one daily credential step."""

    store: CredentialStore
    client: TokenRefreshClient
    alerter: TokenAlerter
    clock: Clock
    gate: RefreshDayGate


class TokenRefresher:
    """Refreshes the stored token, or alerts when it is close to dying."""

    def __init__(self, deps: TokenRefresherDependencies) -> None:
        self._deps = deps

    async def tick(self) -> int:
        """Return 1 when a new token was stored. Other outcomes return 0."""
        now = self._deps.clock.now()
        if not self._deps.gate.claim(now):
            return 0
        stored = await self._deps.store.read(PROVIDER_INSTAGRAM)
        if stored is None or not stored.token:
            return 0
        if not refresh_due(stored, now):
            return 0
        return await self._refresh(stored, now)

    async def _refresh(self, stored: PlainCredential, now: datetime) -> int:
        try:
            grant = await self._deps.client.refresh(_request(stored))
        except TokenRefreshError as exc:
            await self._alert(stored, exc, now)
            return 0
        await self._deps.store.write(_write(grant, now))
        logger.info(LOG_CREDENTIAL_REFRESHED, provider=PROVIDER_INSTAGRAM)
        return 1

    async def _alert(
        self,
        stored: PlainCredential,
        exc: TokenRefreshError,
        now: datetime,
    ) -> None:
        logger.warning(
            LOG_CREDENTIAL_REFRESH_FAILED,
            provider=PROVIDER_INSTAGRAM,
            status_code=exc.status_code,
            error_code=exc.error_code,
        )
        message = alert_message(
            AlertFacts(
                error_code=exc.error_code,
                expires_at=stored.expires_at,
                now=now,
            )
        )
        if message is None:
            return
        await self._deps.alerter.send(message)


def _request(stored: PlainCredential) -> RefreshRequest:
    return RefreshRequest(token=stored.token)


def _write(grant: RefreshGrant, now: datetime) -> WriteCredential:
    return WriteCredential(
        provider=PROVIDER_INSTAGRAM,
        token=grant.access_token,
        expires_at=expiry_after_grant(now, grant.expires_in),
        refreshed_at=now,
    )
