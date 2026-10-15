"""Reply helpers shared by the owner webhook handlers (AE-0370).

Every reply goes through the deferred messenger, so nothing reaches Telegram
before the webhook's unit of work commits.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.application.deferred_replies import (
    DeferredOwnerMessenger,
)
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.domain.owner_ports import (
    CallbackAnswer,
    ForceReplyPrompt,
    MessageEdit,
    OwnerText,
)
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate


class OwnerReplies:
    """Answer, edit, tell, and ask for one webhook update."""

    def __init__(self, messenger: DeferredOwnerMessenger) -> None:
        self._messenger = messenger

    async def finish(self, update: WebhookUpdate, answer: str, text: str) -> None:
        """Toast ``answer`` and replace the message with ``text``, no buttons."""
        await self.answer(update, answer)
        await self.edit(update, text, None)

    async def answer(self, update: WebhookUpdate, text: str) -> None:
        """Stop the button spinner. Text updates have nothing to answer."""
        if not update.callback_id:
            return
        await self._messenger.answer(
            CallbackAnswer(callback_id=update.callback_id, text=text)
        )

    async def edit(
        self,
        update: WebhookUpdate,
        text: str,
        keyboard: InlineKeyboard | None,
    ) -> None:
        """Replace the tapped message's text and buttons."""
        if update.message_id is None or not update.chat_id:
            return
        await self._messenger.edit(
            MessageEdit(
                chat_id=update.chat_id,
                message_id=update.message_id,
                text=text,
                keyboard=keyboard,
            )
        )

    async def tell(
        self,
        update: WebhookUpdate,
        text: str,
        keyboard: InlineKeyboard | None = None,
    ) -> None:
        """Send a new message to the owner's chat."""
        chat_id = update.chat_id or update.actor_id
        if not chat_id:
            return
        await self._messenger.tell(
            OwnerText(chat_id=chat_id, text=text, keyboard=keyboard)
        )

    async def ask(self, update: WebhookUpdate, text: str) -> None:
        """Send a ForceReply prompt."""
        chat_id = update.chat_id or update.actor_id
        await self._messenger.ask(ForceReplyPrompt(chat_id=chat_id, text=text))
