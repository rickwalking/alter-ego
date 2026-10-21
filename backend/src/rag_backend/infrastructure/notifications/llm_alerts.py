"""Logs and Telegram alerts for LLM breaker changes.

Every breaker transition is logged. When ``TELEGRAM_ALERTS_BOT_TOKEN`` and
``TELEGRAM_ALERTS_CHAT_ID`` are set, a send-only bot also messages the owner:
one message per transition, and at most one "all models down" message per
``ALERT_ALL_DOWN_MIN_INTERVAL_SECONDS``. A failed send is logged, never raised,
so an alert can never break a carousel.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
import structlog

from rag_backend.infrastructure.config.llm_queue_constants import (
    ALERT_ALL_DOWN,
    ALERT_ALL_DOWN_MIN_INTERVAL_SECONDS,
    ALERT_CLOSED,
    ALERT_HALF_OPEN,
    ALERT_OPENED,
    ALERT_TIMEOUT_SECONDS,
    LOG_ALERT_FAILED,
    LOG_BREAKER_CLOSED,
    LOG_BREAKER_HALF_OPEN,
    LOG_BREAKER_OPENED,
    TELEGRAM_SEND_URL,
)
from rag_backend.infrastructure.llm.model_breaker import (
    BreakerState,
    BreakerTransition,
)

logger = structlog.get_logger(__name__)

_LOG_EVENTS: dict[BreakerState, str] = {
    BreakerState.OPEN: LOG_BREAKER_OPENED,
    BreakerState.HALF_OPEN: LOG_BREAKER_HALF_OPEN,
    BreakerState.CLOSED: LOG_BREAKER_CLOSED,
}
_SECONDS_PER_MINUTE = 60


def log_transition(transition: BreakerTransition) -> None:
    """Structured log line for every breaker change."""
    logger.warning(
        _LOG_EVENTS[transition.new],
        model=transition.model,
        old=transition.old.value,
        failure=transition.failure.value if transition.failure else None,
        cooldown=transition.cooldown,
        reason=transition.reason[:200],
    )


def alert_text(transition: BreakerTransition) -> str:
    """The Telegram message for one transition."""
    if transition.new is BreakerState.CLOSED:
        return ALERT_CLOSED.format(model=transition.model)
    if transition.new is BreakerState.HALF_OPEN:
        return ALERT_HALF_OPEN.format(model=transition.model)
    minutes = round((transition.cooldown or 0) / _SECONDS_PER_MINUTE)
    return ALERT_OPENED.format(
        model=transition.model,
        failure=transition.failure.value if transition.failure else "?",
        cooldown=f"{minutes} min",
        reason=transition.reason[:200],
    )


@dataclass
class TelegramLlmAlerts:
    """Send-only alerts; a no-op (logs only) without a token and chat id."""

    token: str
    chat_id: str
    clock: Callable[[], float] = time.monotonic
    _last_all_down: float | None = field(default=None)
    _pending: set[asyncio.Task[None]] = field(default_factory=set)

    @property
    def enabled(self) -> bool:
        """True when both the bot token and the chat id are set."""
        return bool(self.token and self.chat_id)

    def on_transition(self, transition: BreakerTransition) -> None:
        """Alert every breaker change except the routine half-open probe."""
        if transition.new is BreakerState.HALF_OPEN:
            return
        self._send(alert_text(transition))

    def on_all_down(self, role: str, summary: str) -> None:
        """Alert "all models down", at most once per interval."""
        now = self.clock()
        last = self._last_all_down
        if last is not None and now - last < ALERT_ALL_DOWN_MIN_INTERVAL_SECONDS:
            return
        self._last_all_down = now
        self._send(ALERT_ALL_DOWN.format(role=role, summary=summary[:600]))

    def _send(self, text: str) -> None:
        if not self.enabled:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        task = loop.create_task(self._post(text))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def _post(self, text: str) -> None:
        url = TELEGRAM_SEND_URL.format(token=self.token)
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            async with httpx.AsyncClient(timeout=ALERT_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(LOG_ALERT_FAILED, error=type(exc).__name__)


__all__ = ["TelegramLlmAlerts", "alert_text", "log_transition"]
