"""Composition root for the conversation module — manual constructor injection.

``bootstrap_module`` wires the conversation application service and the chat
agent factory to their collaborators explicitly. There is no DI framework and no
global container lookup inside the module (ADR-0009 §9) — the inbound edge
constructs the request-scoped collaborators (which enlist in the request's Unit
of Work) and passes them in.

**Behavior-preserving wiring (AE-0100).** The conversation adapters are NOT
relocated in Phase 3; they remain at their legacy locations. The inbound caller
builds them exactly as the legacy routes do today (the request-scoped
``ConversationRepository`` and ``MessageRepository``, plus the bound
``ChatAgentFactory`` that wraps ``build_agent_for_conversation``) and hands them
to this bootstrap. The collaborators are accepted via the typed
:class:`ConversationAdapters` bundle so the function keeps to a single grouped
argument (backend/CLAUDE.md ≤3 args).

The ``PlatformServices`` protocol is a local placeholder (as in the reference
template and the knowledge module) so the module is importable and type-clean
before ``rag_backend.platform`` ships its real type. A real module reads
database/session factories and telemetry from it to build adapters here once it
exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.modules.conversation.application.agent_factory_port import (
    ChatAgentFactory,
)
from rag_backend.modules.conversation.application.service import ConversationService
from rag_backend.modules.conversation.domain.ports import (
    ConversationRepository,
    MessageRepository,
)
from rag_backend.platform.database import UnitOfWork


class PlatformServices(Protocol):
    """Placeholder for the shared platform substrate passed to bootstrap.

    Replaced by ``rag_backend.platform.PlatformServices`` once it exists.
    """


@dataclass(frozen=True)
class ConversationAdapters:
    """Pre-constructed, request-scoped collaborators for the conversation module.

    Built at the inbound edge (the api adapter / legacy route) from the existing
    infrastructure so the module wires to them without relocation (AE-0100). The
    ``unit_of_work`` wraps that same request's ``AsyncSession`` and is the single
    transaction owner the application service commits through (ADR-0009 §9). The
    ``agent_factory`` is the bound :class:`LegacyChatAgentFactory` that wraps the
    legacy agent builders with identical routing + knowledge-facade wiring.
    """

    conversation_repository: ConversationRepository
    message_repository: MessageRepository
    agent_factory: ChatAgentFactory
    unit_of_work: UnitOfWork


@dataclass(frozen=True)
class ConversationModule:
    """Public collaborators returned by :func:`bootstrap_module`.

    Bundles the conversation application service, the chat agent factory, and the
    request-scoped Unit of Work so the inbound edge can resolve conversation
    operations, agent construction, and the single commit boundary through the
    module facade (no behavior change; AE-0101 moves the CRUD/chat routes behind
    handlers that commit via this UoW).
    """

    service: ConversationService
    agent_factory: ChatAgentFactory
    unit_of_work: UnitOfWork


def bootstrap_module(
    platform: PlatformServices,
    adapters: ConversationAdapters,
) -> ConversationModule:
    """Wire the conversation module and return its public collaborators.

    ``platform`` is accepted to demonstrate the ADR-0009 §9 bootstrap signature
    (a real module builds adapters from it once ``rag_backend.platform`` ships).
    For the behavior-preserving phase the caller supplies the already-built
    legacy adapters via ``adapters``; this function injects the repositories into
    the application service via the constructor and exposes the bound agent
    factory unchanged.
    """
    _ = platform  # real modules construct adapters from platform services
    service = ConversationService(
        conversation_repository=adapters.conversation_repository,
        message_repository=adapters.message_repository,
    )
    return ConversationModule(
        service=service,
        agent_factory=adapters.agent_factory,
        unit_of_work=adapters.unit_of_work,
    )
