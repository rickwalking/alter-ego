"""Chat-agent factory port for the conversation bounded context (AE-0100).

The **agent-factory port** is the boundary-safe contract the chat routes and the
streaming service depend on to obtain the conversation's agent: a single
``build_for_conversation(Conversation) -> AlterEgoAgent | RAGAgent`` operation.
Inbound adapters resolve agent construction through the module's public facade
instead of importing ``api/dependencies/agents`` directly, so the routing
decision (``metadata.project_id`` -> AlterEgo vs RAG) and the knowledge-facade
wiring live behind one contract.

The port stays free of SQLAlchemy/FastAPI/Pinecone/container imports — it only
references the module's own domain aggregate (``Conversation``) and the agent
return types. The request-scoped ``AsyncSession`` and the DI container are bound
into the concrete adapter at the inbound edge (see
``infrastructure/chat_agent_factory.py``), mirroring how
``RetrieverSearchAdapter`` binds its retriever in the knowledge module — so the
port itself carries no framework dependency (ADR-0009 §9).
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.rag_agent import RAGAgent
from rag_backend.modules.conversation.domain.models import Conversation


class ChatAgentFactory(Protocol):
    """Contract for building the chat agent bound to a conversation.

    Implemented by the concrete adapter that wraps the existing
    ``build_agent_for_conversation`` (which itself routes on
    ``metadata.project_id`` and wires the AE-0093 knowledge facade). Inbound
    adapters (the chat routes, the streaming service) depend on this port so they
    never reach past the module to construct agents themselves, and so the
    routing + knowledge-facade wiring stay identical (no behavior change).
    """

    def build_for_conversation(
        self, conversation: Conversation
    ) -> AlterEgoAgent | RAGAgent: ...


__all__ = [
    "ChatAgentFactory",
]
