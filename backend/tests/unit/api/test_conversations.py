"""Unit tests for conversation API endpoints.

Feature: Conversation Management
  Scenario: Anonymous user creates conversation
    Given an anonymous user
    When POST /api/conversations
    Then returns 201 with created conversation
    And sets anon_token cookie
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.api.app import create_app
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import Base, close_db


@pytest.fixture
def anon_settings() -> None:
    """Set up test environment with anonymous-compatible settings."""
    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = "test-secret-for-anon-unit-tests!!"
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-anon-unit-tests!"
    yield
    get_settings.cache_clear()


class TestAnonymousConversation:
    """Unit tests for anonymous conversation creation flow."""

    @pytest.mark.asyncio
    async def test_anonymous_creates_conversation(
        self,
        anon_settings: None,
    ) -> None:
        """Given anonymous user, when POST /api/conversations, then returns 201 with conversation."""
        # Arrange: in-memory SQLite database
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        db_config.c_engine = engine

        # Act: anonymous request (no auth headers)
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/conversations/",
                json={"title": "Anonymous Chat", "metadata": {"source": "public"}},
            )

        # Assert
        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "id" in data
        assert data["title"] == "Anonymous Chat"
        # Anonymous conversations should have no user_id set
        assert data.get("user_id") is None

        # Cleanup
        db_config.c_engine = None
        await close_db()
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_anonymous_conversation_sets_anon_cookie(
        self,
        anon_settings: None,
    ) -> None:
        """Given anonymous conversation, when POST /api/conversations, then sets anon_token cookie."""
        # Arrange: in-memory SQLite database
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        db_config.c_engine = engine

        # Act: anonymous request
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/conversations/",
                json={"title": "My Anonymous Chat"},
            )

        # Assert
        assert response.status_code == 201
        anon_cookie = response.cookies.get("anon_token")
        assert anon_cookie is not None, (
            "Expected anon_token cookie to be set for anonymous conversation"
        )
        assert isinstance(anon_cookie, str) and len(anon_cookie) > 0

        # Cleanup
        db_config.c_engine = None
        await close_db()
        await engine.dispose()
