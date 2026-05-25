"""Integration tests for SSE chat streaming endpoints.

# Feature: Alter-Ego Public Chat Streaming
# Scenario: Authenticated user sends a message and receives streamed tokens
#   Given I am authenticated as user "alice"
#   When I POST to "/api/conversations/{conv-id}/chat/stream"
#   Then I receive SSE token events followed by complete

# Feature: Publish Page Carousel Agent Streaming
# Scenario: Authenticated user refines carousel copy
#   Given I am authenticated
#   When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
#   Then I receive SSE token events and tool_result events
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.api.app import create_app

_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
_TEST_JWT_ALGORITHM = "HS256"


def _make_test_token(user_id: str = "test-user-id", role: str = "USER") -> str:
    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "role": role,
        "type": "auth",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm=_TEST_JWT_ALGORITHM)


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch):
    """Override secret keys for all tests in this module."""
    import os

    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = _TEST_JWT_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-key"
    yield
    get_settings.cache_clear()


def _parse_sse_events(text: str) -> list[dict]:
    """Parse raw SSE response text into a list of event dicts."""
    events = []
    buffer = ""
    for line in text.split("\n"):
        if line.startswith("data: "):
            buffer += line[6:]
        elif line == "" and buffer:
            import json

            try:
                events.append(json.loads(buffer))
            except json.JSONDecodeError:
                pass
            buffer = ""
    return events


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


@pytest.fixture
async def test_conversation(client):
    """Create a conversation and return its id."""
    response = await client.post("/api/conversations/", json={"title": "Test Chat"})
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
async def test_user(client):
    """Create a test user and return it."""
    from rag_backend.domain.models import User, UserRole
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import PostgresUserRepository

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresUserRepository(session)
        user = User(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.EDITOR,
            hashed_password="not-used-in-tests",
        )
        created = await repo.create(user)
        await session.commit()
        return created


@pytest.fixture
def mock_agent():
    """Return a mock agent that yields a single token and then completes."""

    async def _mock_chat(*, message: str, conversation_id, stream, persist_messages):
        yield {"type": "token", "content": "Hello"}
        yield {"type": "complete"}

    agent = MagicMock()
    agent.chat = _mock_chat
    return agent


class TestAlterEgoChatStream:
    """Integration tests for Alter-Ego public chat SSE endpoint."""

    @pytest.mark.asyncio
    async def test_anonymous_user_streams_chat(
        self, client, test_conversation, mock_agent, monkeypatch
    ):
        """Given no auth, when POST /chat/stream, then returns SSE token events."""
        # Feature: Alter-Ego Public Chat Streaming
        # Scenario: Anonymous user streams chat without any auth
        from rag_backend.api.routes import chat_stream as chat_stream_module

        monkeypatch.setattr(
            chat_stream_module,
            "build_alter_ego_agent",
            lambda _db, _container: mock_agent,
        )

        response = await client.post(
            f"/api/conversations/{test_conversation}/chat/stream",
            json={"content": "Hello"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = _parse_sse_events(response.text)
        assert any(e.get("type") == "token" for e in events)
        assert any(e.get("type") == "complete" for e in events)

    @pytest.mark.asyncio
    async def test_empty_message_returns_error_event(
        self, client, test_conversation, mock_agent, monkeypatch
    ):
        """Given empty content, when POST /chat/stream, then returns error SSE event."""
        # Feature: Alter-Ego Public Chat Streaming
        # Scenario: User sends empty message
        from rag_backend.api.routes import chat_stream as chat_stream_module

        monkeypatch.setattr(
            chat_stream_module,
            "build_alter_ego_agent",
            lambda _db, _container: mock_agent,
        )

        response = await client.post(
            f"/api/conversations/{test_conversation}/chat/stream",
            json={"content": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_conversation_returns_error_event(
        self, client, mock_agent, monkeypatch
    ):
        """Given invalid conversation id, when POST /chat/stream, then returns error SSE event."""
        # Feature: Alter-Ego Public Chat Streaming
        # Scenario: Chat for non-existent conversation
        from rag_backend.api.routes import chat_stream as chat_stream_module

        monkeypatch.setattr(
            chat_stream_module,
            "build_alter_ego_agent",
            lambda _db, _container: mock_agent,
        )

        response = await client.post(
            "/api/conversations/00000000-0000-0000-0000-000000000000/chat/stream",
            json={"content": "Hello"},
        )

        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        assert any("not found" in str(e.get("content", "")).lower() for e in events)


class TestPublishChatStream:
    """Integration tests for publish chat SSE endpoint."""

    @pytest.mark.asyncio
    async def test_anonymous_user_denied(self, client, test_conversation):
        """Given no auth, when POST /publish-chat/stream, then returns 401."""
        # Feature: Publish Page Carousel Agent Streaming
        # Scenario: Anonymous user attempts publish chat
        response = await client.post(
            f"/api/conversations/{test_conversation}/publish-chat/stream",
            json={"content": "Hello"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_carousel_conversation_returns_400(
        self, client, test_conversation, mock_agent, monkeypatch, test_user
    ):
        """Given conversation without project_id, when POST /publish-chat/stream, then returns 400."""
        # Feature: Publish Page Carousel Agent Streaming
        # Scenario: Publish chat for non-carousel conversation
        from rag_backend.api.routes import chat_stream as chat_stream_module

        monkeypatch.setattr(
            chat_stream_module,
            "build_rag_agent",
            lambda _db, _container: mock_agent,
        )

        token = _make_test_token(user_id=str(test_user.id))
        response = await client.post(
            f"/api/conversations/{test_conversation}/publish-chat/stream",
            json={"content": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
