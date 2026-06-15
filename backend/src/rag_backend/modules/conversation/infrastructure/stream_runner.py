"""Concrete SSE stream-runner adapter for the conversation module (AE-0102).

Private to the module — the facade re-exports the constructor under
``LegacyStreamChatRunner``; cross-module code never imports this path directly.

This adapter satisfies the ``StreamChatRunner`` port (defined in
``modules.conversation.application.streaming``) by **delegating** to the existing
``stream_chat_response`` service in
``rag_backend.application.services.chat_stream_service`` — it does NOT reimplement
the SSE wire. That delegation keeps every behavior byte-identical (AE-0102
Non-Goal: no SSE payload/name change):

* the SSE event types/order (token/sources/complete/error/tool_result), the
  ``id:``/``data:`` framing, the keep-alive ping cadence, and the
  ``Last-Event-ID`` resume numbering are the legacy ``stream_chat_response``
  behavior, unchanged;
* the user-message-persist-then-stream-then-assistant-persist order (committed by
  the legacy service through the request session) is unchanged.

The request-scoped ``AsyncSession`` is bound at construction time (at the inbound
edge, by the DI provider), so the ``run`` operation matches the port's
framework-free signature while the framework dependency (the session and the
``_StreamConfig`` it backs) stays isolated in this infrastructure adapter.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.chat_stream_service import (
    _ChatAgent,
    _StreamConfig,
    stream_chat_response,
)
from rag_backend.modules.conversation.application.streaming import (
    ChatAgentBuilder,
    StreamChatCommand,
)


class LegacyStreamChatRunner:
    """Adapt the legacy ``stream_chat_response`` service to ``StreamChatRunner``.

    Binds the request-scoped session, then delegates each ``run`` call to
    ``stream_chat_response`` so the SSE framing, keep-alive, ``Last-Event-ID``
    resume, and persistence are byte-identical to the legacy stream path.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def run(
        self,
        command: StreamChatCommand,
        agent_builder: ChatAgentBuilder,
    ) -> AsyncIterator[str]:
        # The agent builders return the conversation's ``AlterEgoAgent | RAGAgent``;
        # both satisfy the streaming service's ``_ChatAgent`` protocol structurally
        # (the legacy stream path passed them in directly). The cast records that
        # equivalence at this isolated infrastructure boundary so the strict-typed
        # module application layer stays free of the legacy protocol's shape quirk.
        builder = cast("Callable[[], _ChatAgent]", agent_builder.build)
        config = _StreamConfig(
            conversation_id=command.conversation_id,
            content=command.content,
            db=self._db,
            agent_builder=builder,
            last_event_id=command.last_event_id,
        )
        return stream_chat_response(config)


__all__ = [
    "LegacyStreamChatRunner",
]
