"""Ports for the Telegram owner-action use case. No frameworks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.domain.models import TelegramUpdate


@dataclass(frozen=True, kw_only=True)
class PendingRework:
    """The phase the owner picked, waiting for their next text message."""

    owner_chat_id: str
    run_id: UUID
    phase: str


@dataclass(frozen=True, kw_only=True)
class ReleaseCommand:
    """Make one carousel public. The publishing facade performs the write."""

    project_id: str


@dataclass(frozen=True, kw_only=True)
class CallbackAnswer:
    """``answerCallbackQuery`` body. Stops the button spinner."""

    callback_id: str
    text: str


@dataclass(frozen=True, kw_only=True)
class MessageEdit:
    """Replace the keyboard message. ``keyboard`` None removes the buttons."""

    chat_id: str
    message_id: int
    text: str
    keyboard: InlineKeyboard | None


@dataclass(frozen=True, kw_only=True)
class ForceReplyPrompt:
    """Ask the owner for the rework note."""

    chat_id: str
    text: str


@dataclass(frozen=True, kw_only=True)
class OwnerText:
    """A plain message, used when the update was not a button.

    ``keyboard`` adds inline buttons, e.g. after a typed publish time.
    """

    chat_id: str
    text: str
    keyboard: InlineKeyboard | None = None


class UpdateClaimStore(Protocol):
    """Inserts ``update_id``. False means this delivery was already stored."""

    async def claim_update(self, update: TelegramUpdate) -> bool:
        """Claim one update. False on conflict, without raising."""
        ...


class PendingReworkStore(Protocol):
    """One pending rework per owner. The next text message consumes it."""

    async def put(self, pending: PendingRework) -> None:
        """Remember the phase for this owner, replacing any earlier one."""
        ...

    async def take(self, owner_chat_id: str) -> PendingRework | None:
        """Return and clear the owner's pending phase, or None."""
        ...


class CarouselReleaser(Protocol):
    """Sets ``is_public`` through the publishing facade."""

    async def release(self, command: ReleaseCommand) -> bool:
        """True when the carousel is now public. False when it is missing."""
        ...


class OwnerMessenger(Protocol):
    """Telegram replies for a webhook. Failures are logged, not raised."""

    async def answer(self, command: CallbackAnswer) -> None:
        """Stop the spinner and show a short toast."""
        ...

    async def edit(self, command: MessageEdit) -> None:
        """Replace the keyboard message text and buttons."""
        ...

    async def ask(self, command: ForceReplyPrompt) -> None:
        """Send a ForceReply prompt."""
        ...

    async def tell(self, command: OwnerText) -> None:
        """Send one text message."""
        ...
