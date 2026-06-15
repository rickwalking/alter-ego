"""Concrete chat-agent factory adapter for the conversation module (AE-0100).

Private to the module — the facade re-exports the constructor under
``LegacyChatAgentFactory``; cross-module code never imports this path directly.

This adapter satisfies the ``ChatAgentFactory`` port (defined in
``modules.conversation.application.agent_factory_port``) by **delegating** to the
existing ``build_agent_for_conversation`` in
``rag_backend.api.dependencies.agents`` — it does NOT reimplement the builders.
That delegation keeps every behavior identical (AE-0100 Non-Goal: no agent
behavior change):

* routing on ``metadata.project_id`` -> ``AlterEgoAgent`` vs ``RAGAgent``
  (with the ``user_id is None`` fallback to AlterEgo) is the legacy
  ``build_agent_for_conversation`` logic, unchanged;
* the AE-0093 knowledge-facade wiring (``_build_knowledge_search`` -> the
  ``KnowledgeService`` facade) is the legacy ``build_alter_ego_agent`` /
  ``build_rag_agent`` wiring, unchanged.

The request-scoped ``AsyncSession`` and the DI ``Container`` are bound at
construction time (at the inbound edge, by ``bootstrap_module``), so the
``build_for_conversation`` operation matches the port's framework-free signature
while the framework dependencies stay isolated in this infrastructure adapter.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.rag_agent import RAGAgent
from rag_backend.api.dependencies.agents import build_agent_for_conversation
from rag_backend.infrastructure.container import Container
from rag_backend.modules.conversation.domain.models import Conversation


class LegacyChatAgentFactory:
    """Adapt the legacy agent builders to the ``ChatAgentFactory`` port.

    Binds the request-scoped session and the container, then delegates each
    ``build_for_conversation`` call to ``build_agent_for_conversation`` so the
    routing and knowledge-facade wiring are byte-identical to the legacy path.
    """

    def __init__(self, db: AsyncSession, container: Container) -> None:
        self._db = db
        self._container = container

    @property
    def session(self) -> AsyncSession:
        """The request-scoped session bound into this factory."""
        return self._db

    @property
    def container(self) -> Container:
        """The request-scoped DI container bound into this factory.

        Exposed so the inbound chat adapter can reuse the same container when it
        routes agent construction through its monkeypatch-friendly builder seam
        (AE-0101), keeping the routing + knowledge-facade wiring identical.
        """
        return self._container

    def build_for_conversation(
        self, conversation: Conversation
    ) -> AlterEgoAgent | RAGAgent:
        return build_agent_for_conversation(conversation, self._db, self._container)


__all__ = [
    "LegacyChatAgentFactory",
]
