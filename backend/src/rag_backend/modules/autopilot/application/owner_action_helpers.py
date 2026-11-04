"""Small builders of the owner-action service, kept apart for the line limit."""

from __future__ import annotations

from uuid import UUID

from rag_backend.modules.autopilot.domain.models import TelegramUpdate
from rag_backend.modules.autopilot.domain.owner_ports import (
    ForceReplyPrompt,
    PendingRework,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from rag_backend.modules.autopilot.webhook_constants import TEXT_FORCE_REPLY


def delivery_of(update: WebhookUpdate, clock: Clock) -> TelegramUpdate:
    """The claim record of one webhook delivery."""
    return TelegramUpdate(update_id=update.update_id, received_at=clock.now())


def pending_of(update: WebhookUpdate, run_id: UUID, phase: str) -> PendingRework:
    """The rework the owner's next text answers."""
    return PendingRework(owner_chat_id=update.actor_id, run_id=run_id, phase=phase)


def prompt_of(update: WebhookUpdate) -> ForceReplyPrompt:
    """The force-reply asking the owner what should change."""
    chat_id = update.chat_id or update.actor_id
    return ForceReplyPrompt(chat_id=chat_id, text=TEXT_FORCE_REPLY)


__all__ = ["delivery_of", "pending_of", "prompt_of"]
