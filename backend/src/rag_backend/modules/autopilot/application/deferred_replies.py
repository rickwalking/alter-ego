"""Telegram replies held until the webhook's unit of work commits.

A handler exception rolls back the ``update_id`` claim and every run
transition. Replies sent before that would tell the owner something the
database does not record, so they are buffered and sent only after commit.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    ForceReplyPrompt,
    MessageEdit,
    OwnerMessenger,
    OwnerText,
)

_Reply = Callable[[], Awaitable[None]]


class DeferredOwnerMessenger:
    """``OwnerMessenger`` that queues every call until ``deliver``."""

    def __init__(self, inner: OwnerMessenger) -> None:
        self._inner = inner
        self._queued: list[_Reply] = []

    async def answer(self, command: CallbackAnswer) -> None:
        """Queue ``answerCallbackQuery``."""
        self._queued.append(lambda: self._inner.answer(command))

    async def edit(self, command: MessageEdit) -> None:
        """Queue the keyboard-message edit."""
        self._queued.append(lambda: self._inner.edit(command))

    async def ask(self, command: ForceReplyPrompt) -> None:
        """Queue the ForceReply prompt."""
        self._queued.append(lambda: self._inner.ask(command))

    async def tell(self, command: OwnerText) -> None:
        """Queue one text message."""
        self._queued.append(lambda: self._inner.tell(command))

    async def deliver(self) -> int:
        """Send the queued replies in order. Returns how many were sent."""
        queued, self._queued = self._queued, []
        for reply in queued:
            await reply()
        return len(queued)

    def discard(self) -> int:
        """Drop the queued replies after a rollback. Returns how many."""
        dropped = len(self._queued)
        self._queued = []
        return dropped
