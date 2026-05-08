"""Integration tests for API endpoints."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.api.app import create_app


@pytest.fixture
async def client():
    """Create async test client with in-memory SQLite."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db_config.c_engine = engine

    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


class TestHealthEndpoints:
    """Integration tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Given running server, when GET /health, then returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_readiness_check(self, client):
        """Given running server, when GET /health/ready, then returns dependency status."""
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ready", "unhealthy")
        assert "checks" in data
        assert "database" in data["checks"]
        assert "pinecone" in data["checks"]
        assert "openai" in data["checks"]


class TestDocumentEndpoints:
    """Integration tests for document API endpoints."""

    @pytest.mark.asyncio
    async def test_create_document(self, client):
        """Given valid document data, when POST /api/documents, then returns created document."""
        payload = {
            "title": "Test Document",
            "content": "This is test content for integration testing.",
            "metadata": {"category": "test"},
        }
        response = await client.post("/api/documents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Document"
        assert data["status"] == "pending"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client):
        """Given no documents, when GET /api/documents, then returns empty list."""
        response = await client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_documents_with_data(self, client):
        """Given documents exist, when GET /api/documents, then returns documents."""
        payload = {
            "title": "Integration Test Doc",
            "content": "Content for integration test.",
        }
        await client.post("/api/documents", json=payload)

        response = await client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["title"] == "Integration Test Doc"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client):
        """Given non-existent ID, when GET /api/documents/{id}, then returns 404."""
        response = await client.get("/api/documents/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_document_txt(self, client, monkeypatch):
        """Given a text file, when POST /api/documents/upload, then processes it."""
        import os

        if not os.environ.get("PINECONE_API_KEY"):
            pytest.skip("PINECONE_API_KEY not set")
        content = b"This is a test text file for upload testing."
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", content, "text/plain")},
            data={"title": "Uploaded Test Doc", "tags": "test,integration"},
        )
        assert response.status_code in (201, 500)

    @pytest.mark.asyncio
    async def test_upload_document_empty_file(self, client):
        """Given an empty file, when POST /api/documents/upload, then returns 400."""
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_document_validation_error(self, client):
        """Given invalid data, when POST /api/documents, then returns 422."""
        payload = {"title": ""}
        response = await client.post("/api/documents", json=payload)
        assert response.status_code == 422


class TestConversationEndpoints:
    """Integration tests for conversation API endpoints."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, client):
        """Given valid data, when POST /api/conversations, then returns created conversation."""
        payload = {"title": "Test Conversation", "metadata": {"source": "test"}}
        response = await client.post("/api/conversations", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Conversation"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_conversation_no_title(self, client):
        """Given no title, when POST /api/conversations, then creates with null title."""
        response = await client.post("/api/conversations", json={})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] is None

    @pytest.mark.asyncio
    async def test_list_conversations(self, client):
        """Given conversations exist, when GET /api/conversations, then returns list."""
        await client.post("/api/conversations", json={"title": "Integration Test Conversation"})

        response = await client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, client):
        """Given non-existent ID, when GET /api/conversations/{id}, then returns 404."""
        response = await client.get("/api/conversations/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_conversation_messages_not_found(self, client):
        """Given non-existent conversation, when GET messages, then returns 404."""
        response = await client.get(
            "/api/conversations/00000000-0000-0000-0000-000000000000/messages"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_conversation_crud(self, client):
        """Given a conversation, when CRUD operations, then all succeed."""
        create_response = await client.post("/api/conversations", json={"title": "CRUD Test"})
        assert create_response.status_code == 201
        conv_id = create_response.json()["id"]

        get_response = await client.get(f"/api/conversations/{conv_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "CRUD Test"

        msgs_response = await client.get(f"/api/conversations/{conv_id}/messages")
        assert msgs_response.status_code == 200
        assert msgs_response.json()["items"] == []

        delete_response = await client.delete(f"/api/conversations/{conv_id}")
        assert delete_response.status_code == 204

        get_after = await client.get(f"/api/conversations/{conv_id}")
        assert get_after.status_code == 404


class TestSearchEndpoint:
    """Integration tests for search API endpoint."""

    @pytest.mark.asyncio
    async def test_search_validation(self, client):
        """Given empty query, when POST /api/search, then returns 422."""
        response = await client.post("/api/search", json={"query": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_get_validation(self, client):
        """Given empty query, when GET /api/search, then returns 422."""
        response = await client.get("/api/search", params={"query": ""})
        assert response.status_code == 422


class TestAgentRoutingByMetadata:
    """Integration tests for metadata-based agent routing.

    Feature: Agent Security Boundary — Metadata-Based Agent Routing
    See tests/features/agent_split/security_boundaries.feature

    Scenario: Conversation with project_id metadata routes to RAGAgent (carousel-capable)
      Given a conversation exists with metadata including "project_id" = "abc-123"
      When a chat message is sent to that conversation
      Then the response should include header "X-Agent-Origin: rag-agent"

    Scenario: Conversation without project_id metadata routes to AlterEgoAgent
      Given a conversation exists with empty metadata
      When a chat message is sent to that conversation
      Then the response should include header "X-Agent-Origin: alter-ego"
    """

    @pytest.mark.asyncio
    async def test_carousel_conversation_gets_rag_agent_origin(self, client, monkeypatch):
        """Given a conversation with project_id metadata,
        when a chat message is sent,
        then X-Agent-Origin: rag-agent is returned."""
        from rag_backend.agents.rag_agent import RAGAgent

        async def _mock_agent_chat(*args, **kwargs):
            yield {"type": "complete", "content": "response"}
            yield {"type": "sources", "content": []}

        mock_agent = AsyncMock(spec=RAGAgent)
        mock_agent.chat = _mock_agent_chat

        monkeypatch.setattr(
            "rag_backend.api.dependencies.agents.build_rag_agent",
            lambda _db, _container: mock_agent,
        )

        create_resp = await client.post(
            "/api/conversations",
            json={"title": "Carousel Chat", "metadata": {"project_id": "abc-123"}},
        )
        assert create_resp.status_code == 201
        conv_id = create_resp.json()["id"]

        chat_resp = await client.post(
            f"/api/conversations/{conv_id}/chat",
            json={"content": "refine this carousel"},
        )
        assert chat_resp.status_code == 200
        assert chat_resp.headers.get("X-Agent-Origin") == "rag-agent"

    @pytest.mark.asyncio
    async def test_normal_conversation_gets_alter_ego_origin(self, client, monkeypatch):
        """Given a conversation without project_id metadata,
        when a chat message is sent,
        then X-Agent-Origin: alter-ego is returned."""
        from rag_backend.agents.alter_ego_agent import AlterEgoAgent

        async def _mock_agent_chat(*args, **kwargs):
            yield {"type": "complete", "content": "response"}
            yield {"type": "sources", "content": []}

        mock_agent = AsyncMock(spec=AlterEgoAgent)
        mock_agent.chat = _mock_agent_chat

        monkeypatch.setattr(
            "rag_backend.api.dependencies.agents.build_alter_ego_agent",
            lambda _db, _container: mock_agent,
        )

        create_resp = await client.post(
            "/api/conversations",
            json={"title": "Personal Chat"},
        )
        assert create_resp.status_code == 201
        conv_id = create_resp.json()["id"]

        chat_resp = await client.post(
            f"/api/conversations/{conv_id}/chat",
            json={"content": "search my documents"},
        )
        assert chat_resp.status_code == 200
        assert chat_resp.headers.get("X-Agent-Origin") == "alter-ego"

    @pytest.mark.asyncio
    async def test_metadata_with_other_keys_gets_alter_ego_origin(self, client, monkeypatch):
        """Given a conversation with non-carousel metadata,
        when a chat message is sent,
        then X-Agent-Origin: alter-ego is returned."""
        from rag_backend.agents.alter_ego_agent import AlterEgoAgent

        async def _mock_agent_chat(*args, **kwargs):
            yield {"type": "complete", "content": "response"}
            yield {"type": "sources", "content": []}

        mock_agent = AsyncMock(spec=AlterEgoAgent)
        mock_agent.chat = _mock_agent_chat

        monkeypatch.setattr(
            "rag_backend.api.dependencies.agents.build_alter_ego_agent",
            lambda _db, _container: mock_agent,
        )

        create_resp = await client.post(
            "/api/conversations",
            json={"title": "Source Chat", "metadata": {"source": "web", "user_id": 42}},
        )
        assert create_resp.status_code == 201
        conv_id = create_resp.json()["id"]

        chat_resp = await client.post(
            f"/api/conversations/{conv_id}/chat",
            json={"content": "hello"},
        )
        assert chat_resp.status_code == 200
        assert chat_resp.headers.get("X-Agent-Origin") == "alter-ego"


class TestRateLimiting:
    """Integration tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client):
        """Given any request, when made, then rate limit headers should be present."""
        response = await client.get("/health")
        assert response.status_code == 200
