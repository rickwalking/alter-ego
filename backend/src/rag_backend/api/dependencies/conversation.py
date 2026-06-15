"""Request-scoped DI provider for the conversation module facade.

This is the HTTP-edge composition point for the conversation bounded context. It
resolves the request-scoped collaborators (the conversation and message
repositories) from the DI container, binds the chat-agent factory to the request
session/container, wraps the request ``AsyncSession`` in the platform Unit of
Work (the single commit owner, ADR-0009 §9), and hands them to
``bootstrap_module`` to build the public ``ConversationModule`` facade.

Container resolution happens HERE — at the edge, inside ``api/dependencies/`` —
never inside the module's application code (which composes via ``bootstrap``).
Routes depend on :func:`get_conversation_module`; they never call
``get_container()`` themselves. This mirrors ``api/dependencies/knowledge.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from rag_backend.api.dependencies.knowledge import get_container, get_session
from rag_backend.modules.conversation import (
    ConversationAdapters,
    ConversationHandlers,
    ConversationModule,
    LegacyChatAgentFactory,
    LlmGenerate,
    bootstrap_module,
)
from rag_backend.platform.database import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def get_conversation_module(
    db: AsyncSession = Depends(get_session),
) -> ConversationModule:
    """Build the request-scoped conversation facade for the current request.

    The same ``AsyncSession`` backs the repositories, the agent factory, and the
    Unit of Work, so the repositories' flushes and the UoW's single commit share
    one transaction.
    """
    container = get_container()
    conversation_repository = container.conversation_repository(session=db)
    message_repository = container.message_repository(session=db)
    agent_factory = LegacyChatAgentFactory(db, container)
    unit_of_work = SqlAlchemyUnitOfWork(db)
    adapters = ConversationAdapters(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        agent_factory=agent_factory,
        unit_of_work=unit_of_work,
    )
    return bootstrap_module(platform=container, adapters=adapters)


def get_conversation_handlers(
    module: ConversationModule = Depends(get_conversation_module),
) -> ConversationHandlers:
    """Build the request-scoped conversation handlers from the module facade.

    The CRUD/list/title/messages routes delegate to these handlers; the
    non-streaming chat route builds its own handlers bound to a route-local
    agent factory so the monkeypatch-friendly ``build_agent_for_conversation``
    seam (the AE-0097 safety net) is preserved.
    """
    return ConversationHandlers(
        service=module.service,
        agent_factory=module.agent_factory,
        unit_of_work=module.unit_of_work,
    )


def get_legacy_chat_agent_factory(
    db: AsyncSession = Depends(get_session),
) -> LegacyChatAgentFactory:
    """Build the request-scoped chat-agent factory bound to session + container.

    Returned as the concrete ``LegacyChatAgentFactory`` (not the port) so the
    non-streaming chat route can reuse its bound session/container while routing
    agent construction through its own monkeypatch-friendly builder seam — keeping
    the routing + knowledge-facade wiring identical to the legacy chat path.
    """
    return LegacyChatAgentFactory(db, get_container())


def get_conversation_title_generator() -> LlmGenerate:
    """Resolve the LLM ``generate`` callable for conversation title generation.

    Kept at the edge so the route never reaches the global container itself
    (AE-0101 AC); mirrors how ``get_knowledge_service`` resolves collaborators
    via the container here in ``api/dependencies/``.
    """
    return get_container().llm_service().generate
