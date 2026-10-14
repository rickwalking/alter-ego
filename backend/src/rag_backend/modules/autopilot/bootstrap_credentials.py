"""Startup seed and the daily credential worker step (AE-0358)."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.autopilot.application.credential_seed import (
    SeedCommand,
    seed_instagram_if_absent,
)
from rag_backend.modules.autopilot.application.day_gate import SaoPauloDayGate
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.token_refresher import (
    TokenRefresher,
    TokenRefresherDependencies,
)
from rag_backend.modules.autopilot.credential_constants import (
    LOG_CREDENTIAL_SEEDED,
    LOG_CREDENTIALS_KEY_UNUSABLE,
    PROVIDER_INSTAGRAM,
    PUBLISHING_DISABLED,
)
from rag_backend.modules.autopilot.infrastructure.credential_cipher import (
    FernetTokenCipher,
    encryption_key_problem,
    encryption_key_usable,
)
from rag_backend.modules.autopilot.infrastructure.credential_store import (
    SqlCredentialStore,
)
from rag_backend.modules.autopilot.infrastructure.instagram_token_client import (
    HttpxInstagramTokenClient,
)
from rag_backend.modules.autopilot.infrastructure.stored_token_provider import (
    build_stored_instagram_token_provider,
)
from rag_backend.modules.autopilot.infrastructure.token_alert import (
    TelegramAlertConfig,
    TelegramTokenAlerter,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class CredentialTickConfig:
    """Process-wide secrets for the daily refresh. The session arrives per tick."""

    encryption_key: str
    bot_token: str
    chat_id: str


class CredentialRefreshTickAdapter:
    """One daily Instagram token check on the worker tick's session."""

    def __init__(self, config: CredentialTickConfig) -> None:
        self._config = config
        self._gate = SaoPauloDayGate()

    async def tick(self, db: AsyncSession) -> int:
        """Refresh when the token is due. Returns 1 when a new token is stored."""
        refresher = TokenRefresher(_dependencies(db, self._config, self._gate))
        return await refresher.tick()


def build_credential_refresh_tick(
    config: CredentialTickConfig,
) -> CredentialRefreshTickAdapter:
    """Build the worker collaborator. The day gate lives for the process."""
    return CredentialRefreshTickAdapter(config)


def credential_tick_config(settings: Settings) -> CredentialTickConfig | None:
    """Refresh config, or None when the Fernet key cannot encrypt."""
    key = settings.credentials_encryption_key.get_secret_value()
    if not encryption_key_usable(key):
        return None
    return CredentialTickConfig(
        encryption_key=key,
        bot_token=settings.telegram_bot_token.get_secret_value(),
        chat_id=settings.telegram_owner_chat_id,
    )


async def prepare_instagram_credentials(settings: Settings) -> None:
    """Warn when the Fernet key is unusable, otherwise seed the env token once."""
    key = settings.credentials_encryption_key.get_secret_value()
    problem = encryption_key_problem(key)
    if problem is not None:
        logger.warning(
            LOG_CREDENTIALS_KEY_UNUSABLE,
            reason=problem,
            publishing=PUBLISHING_DISABLED,
        )
        return
    token = settings.meta_ig_access_token.get_secret_value()
    if not token.strip():
        return
    await _seed(key, token)


async def _seed(key: str, token: str) -> None:
    maker = get_session_maker()
    async with maker() as session:
        try:
            inserted = await seed_instagram_if_absent(
                SeedCommand(
                    store=SqlCredentialStore(session, FernetTokenCipher(key)),
                    token=token,
                    now=SystemClock().now(),
                )
            )
        except IntegrityError:
            await session.rollback()
            return
        if not inserted:
            return
        await session.commit()
        logger.info(LOG_CREDENTIAL_SEEDED, provider=PROVIDER_INSTAGRAM)


def _dependencies(
    session: AsyncSession,
    config: CredentialTickConfig,
    gate: SaoPauloDayGate,
) -> TokenRefresherDependencies:
    return TokenRefresherDependencies(
        store=SqlCredentialStore(session, FernetTokenCipher(config.encryption_key)),
        client=HttpxInstagramTokenClient(),
        alerter=TelegramTokenAlerter(
            TelegramAlertConfig(bot_token=config.bot_token, chat_id=config.chat_id)
        ),
        clock=SystemClock(),
        gate=gate,
    )


__all__ = [
    "CredentialRefreshTickAdapter",
    "CredentialTickConfig",
    "build_credential_refresh_tick",
    "build_stored_instagram_token_provider",
    "credential_tick_config",
    "encryption_key_usable",
    "prepare_instagram_credentials",
]
