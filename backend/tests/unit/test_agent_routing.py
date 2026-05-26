"""Unit tests for metadata-based agent routing.

Feature: Agent Security Boundary — Metadata-Based Agent Routing
See tests/features/agent_split/security_boundaries.feature
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.api.dependencies.agents import CONVERSATION_METADATA_PROJECT_ID
from rag_backend.domain.models import Conversation


class TestMetadataRoutingDecision:
    """Test the pure routing decision logic.

    The routing function checks conversation.metadata for project_id.
    If present: RAGAgent (carousel-capable). If absent: AlterEgoAgent (KB only).

    Scenario: build_agent_for_conversation selects RAGAgent when project_id present
      Given a Conversation with metadata {"project_id": "abc"}
      When build_agent_for_conversation is called
      Then build_rag_agent is called (not build_alter_ego_agent)

    Scenario: build_agent_for_conversation selects AlterEgoAgent when no project_id
      Given a Conversation with empty metadata
      When build_agent_for_conversation is called
      Then build_alter_ego_agent is called (not build_rag_agent)
    """

    @pytest.mark.asyncio
    async def test_routes_to_rag_agent_when_project_id_present(self):
        from rag_backend.api.dependencies.agents import build_agent_for_conversation

        conversation = Conversation(
            id=uuid4(),
            metadata={CONVERSATION_METADATA_PROJECT_ID: "abc-123"},
        )
        db = AsyncMock()
        container = MagicMock()

        with (
            patch(
                "rag_backend.api.dependencies.agents.build_rag_agent"
            ) as mock_build_rag,
            patch(
                "rag_backend.api.dependencies.agents.build_alter_ego_agent"
            ) as mock_build_alter,
        ):
            mock_build_rag.return_value = MagicMock()
            mock_build_alter.return_value = MagicMock()

            agent = build_agent_for_conversation(conversation, db, container)

            mock_build_rag.assert_called_once_with(db, container)
            mock_build_alter.assert_not_called()
            assert agent == mock_build_rag.return_value

    @pytest.mark.asyncio
    async def test_routes_to_alter_ego_when_metadata_empty(self):
        from rag_backend.api.dependencies.agents import build_agent_for_conversation

        conversation = Conversation(
            id=uuid4(),
            metadata={},
        )
        db = AsyncMock()
        container = MagicMock()

        with (
            patch(
                "rag_backend.api.dependencies.agents.build_rag_agent"
            ) as mock_build_rag,
            patch(
                "rag_backend.api.dependencies.agents.build_alter_ego_agent"
            ) as mock_build_alter,
        ):
            mock_build_rag.return_value = MagicMock()
            mock_build_alter.return_value = MagicMock()

            agent = build_agent_for_conversation(conversation, db, container)

            mock_build_alter.assert_called_once_with(db, container)
            mock_build_rag.assert_not_called()
            assert agent == mock_build_alter.return_value

    @pytest.mark.asyncio
    async def test_routes_to_alter_ego_when_metadata_has_other_keys(self):
        from rag_backend.api.dependencies.agents import build_agent_for_conversation

        conversation = Conversation(
            id=uuid4(),
            metadata={"source": "web", "user_id": 42},
        )
        db = AsyncMock()
        container = MagicMock()

        with (
            patch(
                "rag_backend.api.dependencies.agents.build_rag_agent"
            ) as mock_build_rag,
            patch(
                "rag_backend.api.dependencies.agents.build_alter_ego_agent"
            ) as mock_build_alter,
        ):
            mock_build_rag.return_value = MagicMock()
            mock_build_alter.return_value = MagicMock()

            agent = build_agent_for_conversation(conversation, db, container)

            mock_build_alter.assert_called_once_with(db, container)
            mock_build_rag.assert_not_called()
            assert agent == mock_build_alter.return_value


class TestBuildAlterEgoAgent:
    """Verify AlterEgoAgent has no carousel tools."""

    def test_alter_ego_agent_tools_exclude_carousel(self):
        from rag_backend.infrastructure.config.settings import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.anthropic_api_key = "test"
        mock_settings.anthropic_model = "claude-test"

        agent = AlterEgoAgent(
            settings=mock_settings,
            retriever=AsyncMock(),
            message_repository=AsyncMock(),
            document_repository=AsyncMock(),
        )

        tool_names = [t.name.lstrip("_") for t in agent._build_tools()]

        forbidden_tools = [
            "generate_carousel",
            "refine_carousel_copy",
            "regenerate_slide_image",
            "refine_carousel_design",
        ]

        for forbidden in forbidden_tools:
            assert forbidden not in tool_names, (
                f"SECURITY VIOLATION: {forbidden} found in AlterEgoAgent!"
            )

        expected_tools = {"search_documents", "list_documents"}
        assert set(tool_names) == expected_tools, (
            f"AlterEgoAgent tools mismatch. Expected {expected_tools}, got {set(tool_names)}"
        )
