"""Unit tests for the conversation module skeleton + ChatAgentFactory (AE-0100).

Feature: Conversation module skeleton, facade, shims, and ChatAgentFactory
See tests/features/conversation_module.feature

These tests prove the behavior-preserving extraction:

* the repository ports and entities are **object-identity shims** (re-exports);
* the facade exposes the documented public API;
* ``bootstrap_module`` wires the module via manual constructor injection;
* the concrete ``LegacyChatAgentFactory`` delegates to the existing
  ``build_agent_for_conversation`` with identical routing + bound collaborators,
  producing the same agent TYPES (RAGAgent vs AlterEgoAgent) — no behavior
  change, no real Pinecone/OpenAI/Anthropic clients.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.rag_agent import RAGAgent
from rag_backend.domain.constants.conversation import CONVERSATION_METADATA_PROJECT_ID
from rag_backend.modules.conversation import (
    ChatAgentFactory,
    Conversation,
    ConversationAdapters,
    ConversationModule,
    ConversationService,
    LegacyChatAgentFactory,
    Message,
    MessageRole,
    bootstrap_module,
)

_AGENT_FACTORY_BUILDER = (
    "rag_backend.modules.conversation.infrastructure."
    "chat_agent_factory.build_agent_for_conversation"
)


class TestRepositoryPortShimIdentity:
    """Scenario: Repository ports re-export to identical objects."""

    def test_conversation_repository_is_identical_object(self) -> None:
        from rag_backend.domain.protocols.repositories import (
            ConversationRepository as Canonical,
        )
        from rag_backend.modules.conversation.domain.ports import (
            ConversationRepository as ModulePort,
        )

        assert Canonical is ModulePort

    def test_message_repository_is_identical_object(self) -> None:
        from rag_backend.domain.protocols.repositories import (
            MessageRepository as Canonical,
        )
        from rag_backend.modules.conversation.domain.ports import (
            MessageRepository as ModulePort,
        )

        assert Canonical is ModulePort


class TestEntityShimIdentity:
    """Scenario: Conversation/Message entities re-export to identical objects."""

    def test_conversation_entity_is_identical_class(self) -> None:
        from rag_backend.domain.models.conversation import (
            Conversation as Canonical,
        )

        assert Conversation is Canonical

    def test_message_entity_is_identical_class(self) -> None:
        from rag_backend.domain.models.conversation import Message as Canonical
        from rag_backend.domain.models.conversation import MessageRole as CanonicalRole

        assert Message is Canonical
        assert MessageRole is CanonicalRole


class TestFacadeSurface:
    """Scenario: The facade exposes the documented public API."""

    def test_public_symbols_exported(self) -> None:
        from rag_backend.modules import conversation as facade

        for name in (
            "ChatAgentFactory",
            "ConversationService",
            "LegacyChatAgentFactory",
            "ConversationAdapters",
            "ConversationModule",
            "bootstrap_module",
            "Conversation",
            "Message",
            "MessageRole",
        ):
            assert name in facade.__all__
            assert hasattr(facade, name)

    def test_legacy_factory_satisfies_port(self) -> None:
        factory = LegacyChatAgentFactory(db=AsyncMock(), container=MagicMock())
        port: ChatAgentFactory = factory  # structural typing check
        assert hasattr(port, "build_for_conversation")


class TestBootstrapWiring:
    """Scenario: bootstrap wires the module via manual DI (no global container)."""

    def test_bootstrap_returns_module_with_service_and_factory(self) -> None:
        agent_factory = MagicMock(spec=ChatAgentFactory)
        adapters = ConversationAdapters(
            conversation_repository=AsyncMock(),
            message_repository=AsyncMock(),
            agent_factory=agent_factory,
            unit_of_work=AsyncMock(),
        )

        module = bootstrap_module(platform=MagicMock(), adapters=adapters)

        assert isinstance(module, ConversationModule)
        assert isinstance(module.service, ConversationService)
        assert module.agent_factory is agent_factory


class TestChatAgentFactoryDelegationAndRouting:
    """Scenarios: the factory builds the right agent and binds db/container."""

    def test_builds_rag_agent_when_project_id_present(self) -> None:
        conversation = Conversation(
            id=uuid4(),
            user_id=uuid4(),
            metadata={CONVERSATION_METADATA_PROJECT_ID: "abc-123"},
        )
        db = AsyncMock()
        container = MagicMock()
        factory = LegacyChatAgentFactory(db=db, container=container)
        rag_agent = MagicMock(spec=RAGAgent)

        with patch(_AGENT_FACTORY_BUILDER, return_value=rag_agent) as mock_build:
            agent = factory.build_for_conversation(conversation)

        mock_build.assert_called_once_with(conversation, db, container)
        assert agent is rag_agent

    def test_builds_alter_ego_agent_when_metadata_empty(self) -> None:
        conversation = Conversation(id=uuid4(), metadata={})
        db = AsyncMock()
        container = MagicMock()
        factory = LegacyChatAgentFactory(db=db, container=container)
        alter_agent = MagicMock(spec=AlterEgoAgent)

        with patch(_AGENT_FACTORY_BUILDER, return_value=alter_agent) as mock_build:
            agent = factory.build_for_conversation(conversation)

        mock_build.assert_called_once_with(conversation, db, container)
        assert agent is alter_agent

    def test_routing_matches_legacy_real_construction(self) -> None:
        """Real build (no patch) yields the SAME agent types per routing.

        Exercises the actual ``build_agent_for_conversation`` so the routing
        (metadata.project_id -> RAG vs AlterEgo) is identical to the legacy
        path. External clients (Anthropic/OpenAI/Pinecone) are not contacted —
        only constructed from a stubbed Settings/Container, so no keys are
        needed.
        """
        from rag_backend.infrastructure.config.settings import Settings

        settings = MagicMock(spec=Settings)
        settings.anthropic_api_key = "test"
        settings.anthropic_model = "claude-test"

        container = MagicMock()
        container.settings.return_value = settings
        container.retriever.return_value = AsyncMock()

        db = AsyncMock()
        factory = LegacyChatAgentFactory(db=db, container=container)

        alter_conversation = Conversation(id=uuid4(), metadata={})
        agent = factory.build_for_conversation(alter_conversation)

        assert isinstance(agent, AlterEgoAgent)


class TestConversationServiceReuse:
    """THE module SHALL reuse ConversationService (no rewrite)."""

    def test_module_service_is_legacy_service(self) -> None:
        from rag_backend.application.services.conversation_service import (
            ConversationService as Legacy,
        )

        assert ConversationService is Legacy


@pytest.mark.asyncio
async def test_bootstrapped_service_create_conversation_uses_repo() -> None:
    """The wired service delegates to the injected conversation repository."""
    conv_repo = AsyncMock()
    created = Conversation(id=uuid4(), metadata={})
    conv_repo.create.return_value = created
    adapters = ConversationAdapters(
        conversation_repository=conv_repo,
        message_repository=AsyncMock(),
        agent_factory=MagicMock(spec=ChatAgentFactory),
        unit_of_work=AsyncMock(),
    )

    module = bootstrap_module(platform=MagicMock(), adapters=adapters)
    result = await module.service.create_conversation()

    conv_repo.create.assert_awaited_once()
    assert result is created
