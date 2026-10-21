"""Tell the owner that the Grok Bot scout could not finish.

The message is one Telegram status send through the owner notifier.
The reason is inert text: it is not interpreted as an instruction.

Status notices require a run id. A scout failure is not a run, so it uses the
nil ``_SCOUT_RUN_ID``, which is not sent to Telegram when the keyboard is empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

import structlog

from rag_backend.modules.autopilot.constants import (
    DETAIL_SCOUT_NOTIFY_FAILED,
    DETAIL_SCOUT_NOTIFY_UNCONFIGURED,
    DETAIL_SCOUT_REASON_EMPTY,
    LOG_SCOUT_FAILED,
    SCOUT_FAILED_PREFIX,
)
from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    TelegramDeliveryError,
)
from rag_backend.modules.autopilot.domain.notify import StatusNotice
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.scout_ports import (
    ScoutFailureEntry,
    ScoutFailureLog,
    StatusSender,
)
from rag_backend.modules.autopilot.domain.topic_text import (
    contains_url,
    strip_controls,
)
from rag_backend.modules.autopilot.scout_constants import (
    DETAIL_SCOUT_DAILY_CAP,
    DETAIL_SCOUT_DUPLICATE,
    SCOUT_FAILURE_WINDOW_HOURS,
    SCOUT_FAILURES_PER_DAY,
)

logger = structlog.get_logger()

_SCOUT_RUN_ID = UUID(int=0)


@dataclass(frozen=True, kw_only=True)
class ScoutFailureDependencies:
    """Notifier, the owner chat, and the delivered-failure log.

    An empty chat id cannot deliver. The log bounds Telegram to three
    distinct reasons per rolling 24 hours (QA r1 S-W3).
    """

    notifier: StatusSender
    chat_id: str
    log: ScoutFailureLog
    clock: Clock


@dataclass(frozen=True, kw_only=True)
class ScoutFailureCommand:
    """The reason the bot reported. At most 500 characters after schema."""

    reason: str


@dataclass(frozen=True, kw_only=True)
class ScoutFailureResult:
    """``error`` is None when the owner was sent exactly one message."""

    delivered: bool
    error: str | None


class ScoutFailureService:
    """Send one status message containing the scout's reason."""

    def __init__(self, deps: ScoutFailureDependencies) -> None:
        self._deps = deps

    async def report(self, command: ScoutFailureCommand) -> ScoutFailureResult:
        """Deliver the reason, or return a stable error code and send nothing."""
        cleaned = without_urls(strip_controls(command.reason))
        chat_id = self._deps.chat_id.strip()
        blocked = _blocked(cleaned, chat_id)
        if blocked is not None:
            return _undelivered(blocked)
        await self._deps.log.lock()
        try:
            return await self._report_locked(cleaned, chat_id)
        finally:
            await self._deps.log.commit()

    async def _report_locked(self, cleaned: str, chat_id: str) -> ScoutFailureResult:
        """Cap check, send, and record, serialized by the log lock (QA r2 R7)."""
        suppressed = await self._suppressed(cleaned)
        if suppressed is not None:
            return _undelivered(suppressed)
        try:
            await self._deps.notifier.send_status(_notice(chat_id, cleaned))
        except NotifierUnconfiguredError:
            return _undelivered(DETAIL_SCOUT_NOTIFY_UNCONFIGURED)
        except TelegramDeliveryError:
            return _undelivered(DETAIL_SCOUT_NOTIFY_FAILED)
        await self._remember(cleaned)
        logger.info(LOG_SCOUT_FAILED, delivered=True)
        return ScoutFailureResult(delivered=True, error=None)

    async def _suppressed(self, reason: str) -> str | None:
        since = self._deps.clock.now() - timedelta(hours=SCOUT_FAILURE_WINDOW_HOURS)
        sent = await self._deps.log.reasons_since(since)
        if reason in sent:
            return DETAIL_SCOUT_DUPLICATE
        if len(sent) >= SCOUT_FAILURES_PER_DAY:
            return DETAIL_SCOUT_DAILY_CAP
        return None

    async def _remember(self, reason: str) -> None:
        entry = ScoutFailureEntry(reason=reason, sent_at=self._deps.clock.now())
        await self._deps.log.record(entry)


def without_urls(reason: str) -> str:
    """Drop every whitespace-separated token that carries a URL."""
    kept = [word for word in reason.split() if not contains_url(word)]
    return " ".join(kept)


def failure_text(reason: str) -> str:
    """Owner-visible text. ``reason`` is included and is not a command."""
    return f"{SCOUT_FAILED_PREFIX}{reason}"


def _blocked(reason: str, chat_id: str) -> str | None:
    if reason == "":
        return DETAIL_SCOUT_REASON_EMPTY
    if chat_id == "":
        return DETAIL_SCOUT_NOTIFY_UNCONFIGURED
    return None


def _undelivered(error: str) -> ScoutFailureResult:
    logger.info(LOG_SCOUT_FAILED, delivered=False, error=error)
    return ScoutFailureResult(delivered=False, error=error)


def _notice(chat_id: str, reason: str) -> StatusNotice:
    return StatusNotice(
        chat_id=chat_id,
        run_id=_SCOUT_RUN_ID,
        text=failure_text(reason),
        keyboard=None,
    )
