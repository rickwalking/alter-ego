"""Tell the owner that the Grok Bot scout could not finish.

The message is one Telegram status send through the AE-0355 notifier.
The reason is inert text: it is not interpreted as an instruction.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from rag_backend.modules.autopilot.domain.scout_ports import StatusSender
from rag_backend.modules.autopilot.domain.topic_text import strip_controls

logger = structlog.get_logger()

# Status notices require a run id. A scout failure is not a run, and the id
# is not sent to Telegram when the keyboard is empty.
_SCOUT_RUN_ID = UUID(int=0)


@dataclass(frozen=True, kw_only=True)
class ScoutFailureDependencies:
    """Notifier and the owner chat. An empty chat id cannot deliver."""

    notifier: StatusSender
    chat_id: str


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
        cleaned = strip_controls(command.reason)
        chat_id = self._deps.chat_id.strip()
        blocked = _blocked(cleaned, chat_id)
        if blocked is not None:
            return _undelivered(blocked)
        try:
            await self._deps.notifier.send_status(_notice(chat_id, cleaned))
        except NotifierUnconfiguredError:
            return _undelivered(DETAIL_SCOUT_NOTIFY_UNCONFIGURED)
        except TelegramDeliveryError:
            return _undelivered(DETAIL_SCOUT_NOTIFY_FAILED)
        logger.info(LOG_SCOUT_FAILED, delivered=True)
        return ScoutFailureResult(delivered=True, error=None)


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
