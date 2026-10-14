"""One-shot Telegram status send for a scout failure.

The HTTP client is opened for the call and closed before returning, so a
request does not keep a connection. Tests inject a ``StatusSender`` instead.
"""

from __future__ import annotations

import httpx

from rag_backend.modules.autopilot.domain.notify import StatusNotice, StatusSendResult
from rag_backend.modules.autopilot.domain.ports import Sleeper
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
    TelegramClientConfig,
    TelegramNotifier,
)
from rag_backend.modules.autopilot.notify_constants import TELEGRAM_HTTP_TIMEOUT_SECONDS


class ClosingTelegramStatus:
    """``StatusSender`` that closes its client after one ``sendMessage``."""

    def __init__(self, token: str, sleeper: Sleeper) -> None:
        self._token = token
        self._sleeper = sleeper

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        """Deliver ``notice`` and close the client, including on failure."""
        async with httpx.AsyncClient(
            timeout=TELEGRAM_HTTP_TIMEOUT_SECONDS,
            trust_env=False,
        ) as client:
            notifier = TelegramNotifier(
                TelegramClientConfig(
                    token=self._token,
                    sleeper=self._sleeper,
                    client=client,
                )
            )
            return await notifier.send_status(notice)
