"""Telegram alert for a failing Instagram token. The bot token is not logged."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx
import structlog

from rag_backend.modules.autopilot.credential_constants import (
    LOG_CREDENTIAL_ALERT_FAILED,
    LOG_CREDENTIAL_ALERT_SKIPPED,
)
from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    TelegramDeliveryError,
    TelegramRateLimitedError,
)
from rag_backend.modules.autopilot.domain.notify import StatusNotice
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
    AsyncSleeper,
    TelegramClientConfig,
    TelegramNotifier,
)
from rag_backend.modules.autopilot.notify_constants import TELEGRAM_HTTP_TIMEOUT_SECONDS

logger = structlog.get_logger()

# Status notices require a run id. A credential is not a run, and the id is
# not sent to Telegram when the keyboard is empty.
_ALERT_RUN_ID = UUID(int=0)


@dataclass(frozen=True, kw_only=True)
class TelegramAlertConfig:
    """Bot credentials. An empty token or chat id makes ``send`` a no-op."""

    bot_token: str
    chat_id: str
    client: httpx.AsyncClient | None = None


class TelegramTokenAlerter:
    """Posts the regeneration instructions with ``sendMessage``."""

    def __init__(self, config: TelegramAlertConfig) -> None:
        self._config = config

    async def send(self, message: str) -> None:
        """Deliver ``message``. Transport failures are logged without the token."""
        token = self._config.bot_token.strip()
        chat_id = self._config.chat_id.strip()
        if not token or not chat_id:
            logger.info(LOG_CREDENTIAL_ALERT_SKIPPED)
            return
        try:
            await self._post(token, chat_id, message)
        except (
            TelegramDeliveryError,
            NotifierUnconfiguredError,
            TelegramRateLimitedError,
        ):
            logger.warning(LOG_CREDENTIAL_ALERT_FAILED)

    async def _post(self, token: str, chat_id: str, message: str) -> None:
        if self._config.client is not None:
            await _send(
                _Outgoing(
                    token=token,
                    chat_id=chat_id,
                    message=message,
                    client=self._config.client,
                )
            )
            return
        async with httpx.AsyncClient(
            timeout=TELEGRAM_HTTP_TIMEOUT_SECONDS,
            trust_env=False,
        ) as client:
            await _send(
                _Outgoing(
                    token=token,
                    chat_id=chat_id,
                    message=message,
                    client=client,
                )
            )


@dataclass(frozen=True, kw_only=True)
class _Outgoing:
    """One ``sendMessage`` attempt."""

    token: str
    chat_id: str
    message: str
    client: httpx.AsyncClient


async def _send(outgoing: _Outgoing) -> None:
    notifier = TelegramNotifier(
        TelegramClientConfig(
            token=outgoing.token,
            sleeper=AsyncSleeper(),
            client=outgoing.client,
        )
    )
    notice = StatusNotice(
        chat_id=outgoing.chat_id,
        run_id=_ALERT_RUN_ID,
        text=outgoing.message,
        keyboard=None,
    )
    await notifier.send_status(notice)
