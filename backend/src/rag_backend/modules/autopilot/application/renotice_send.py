"""Send a re-sent escalation notice at most once, whatever happens around the send.

The notifier records a send when its step commits, so a crash or a rollback after
the send would forget it and the notice would go out again. A claim committed first
closes that window: it is released only when the send certainly did not happen.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.modules.autopilot.domain.escalation_renotice import RenoticeClaims
from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    RenoticeClaimedError,
    TelegramDeliveryError,
    TelegramDeliveryUnknownError,
)
from rag_backend.modules.autopilot.domain.notify import (
    AutopilotOutboxEvent,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.notify_constants import (
    EVENT_TYPE_ESCALATION_RENOTICE,
)


class StatusSender(Protocol):
    """What delivers one status notice."""

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        """Send one status message."""
        ...


class _ClaimedSend:
    """Take the claim, send, and release only a send that did not happen."""

    def __init__(
        self,
        sender: StatusSender,
        claims: RenoticeClaims,
        event: AutopilotOutboxEvent,
    ) -> None:
        self._sender = sender
        self._claims = claims
        self._event = event

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        run_id, event_id = self._event.run_id, self._event.event_id
        if not await self._claims.take(run_id, event_id):
            raise RenoticeClaimedError
        try:
            return await self._sender.send_status(notice)
        except TelegramDeliveryUnknownError:
            raise
        except (TelegramDeliveryError, NotifierUnconfiguredError):
            await self._claims.release(run_id, event_id)
            raise


def status_sender(
    sender: StatusSender,
    claims: RenoticeClaims,
    event: AutopilotOutboxEvent,
) -> StatusSender:
    """``sender``, wrapped in the claim for a re-sent escalation notice."""
    if event.event_type != EVENT_TYPE_ESCALATION_RENOTICE:
        return sender
    return _ClaimedSend(sender, claims, event)


__all__ = ["StatusSender", "status_sender"]
