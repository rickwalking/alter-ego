"""Streaming chat use case for the conversation bounded context (AE-0102).

Private to the module — the public facade re-exports the streaming handler and
its command/ports; cross-module code never imports this path directly. The
streaming handler is the use-case entry point the thin SSE route adapters
(``chat_stream.py``) delegate to so that agent construction and the SSE
orchestration go through one module contract.

Behavior-preserving (AE-0102): the handler does NOT reimplement the SSE wire. It
delegates to an injected :class:`StreamChatRunner` port (the concrete adapter
wraps the existing ``stream_chat_response`` service), so the SSE event
types/order (token/sources/complete/error/tool_result), the ``id:``/``data:``
framing, the keep-alive ping cadence, ``Last-Event-ID`` resume, and the
persistence-then-stream order stay byte-identical to the legacy path. The agent
is built through a :class:`ChatAgentBuilder` (bound at the edge to the
``ChatAgentFactory`` adapter + the monkeypatch-friendly builder seam), so the
``metadata.project_id`` AlterEgo/RAG routing and the AE-0093 knowledge-facade
wiring stay identical.

The application layer imports only ports, framework-free types, and the agent
return types — never a concrete Postgres repository, the SSE service's
``AsyncSession``-bound config, or the global container (AE-0102 AC). The
request-scoped session is bound into the concrete runner adapter at the inbound
edge (see ``infrastructure/stream_runner.py``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.rag_agent import RAGAgent


@dataclass(frozen=True)
class StreamChatCommand:
    """Parsed SSE chat request carried from the route into the handler.

    Framework-free: only the conversation id, the message content, and the
    optional ``Last-Event-ID`` resume cursor. The request-scoped session is
    bound into the runner adapter at the edge, never carried here.
    """

    conversation_id: UUID
    content: str
    last_event_id: int | None = None


class ChatAgentBuilder(Protocol):
    """Boundary-safe builder for the conversation's chat agent.

    Implemented at the inbound edge by a route-local builder that reuses the
    ``ChatAgentFactory`` adapter's bound session/container and routes agent
    construction through the module-level builder seam (so the AE-0097 safety net
    keeps overriding agent construction). The handler stays free of any
    framework or container reference.
    """

    def build(self) -> AlterEgoAgent | RAGAgent: ...


class StreamChatRunner(Protocol):
    """Boundary-safe SSE stream runner for a single chat turn.

    Implemented by the concrete adapter that wraps the legacy
    ``stream_chat_response`` service (which owns the SSE framing, keep-alive,
    ``Last-Event-ID`` numbering, and message persistence). The request-scoped
    session is bound into the adapter at the edge, so the port itself carries no
    framework dependency.
    """

    def run(
        self,
        command: StreamChatCommand,
        agent_builder: ChatAgentBuilder,
    ) -> AsyncIterator[str]: ...


class ConversationStreamHandler:
    """Use-case handler for SSE chat streaming.

    Constructed per request by the inbound edge from the bound
    :class:`StreamChatRunner`. Holds no framework state and resolves no global
    container; the SSE wire + persistence stay in the runner adapter so the
    event types/order, framing, keep-alive, and ``Last-Event-ID`` resume are
    byte-identical to the legacy path.
    """

    def __init__(self, runner: StreamChatRunner) -> None:
        self._runner = runner

    def stream(
        self,
        command: StreamChatCommand,
        agent_builder: ChatAgentBuilder,
    ) -> AsyncIterator[str]:
        """Stream the SSE chat response for ``command`` using ``agent_builder``.

        The agent is built lazily (inside the runner) so the monkeypatch-friendly
        builder seam still overrides construction, and so the agent is created
        only after the conversation/limit checks have passed at the edge.
        """
        return self._runner.run(command, agent_builder)


__all__ = [
    "ChatAgentBuilder",
    "ConversationStreamHandler",
    "StreamChatCommand",
    "StreamChatRunner",
]
