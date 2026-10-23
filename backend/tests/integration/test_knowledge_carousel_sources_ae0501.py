"""The Knowledge Base lists the content sources of the caller's carousels."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.models import User, UserRole
from tests.integration.conftest import (
    TEST_SECRET,
    auth_headers_for,
    create_test_user,
)

_URL = "/api/knowledge/carousel-sources"
_BASE_TIME = datetime(2026, 10, 1, tzinfo=UTC)


@dataclass
class _Env:
    app: FastAPI
    owner: User

    def client_for(self, user: User | None) -> AsyncClient:
        headers = auth_headers_for(user) if user else {}
        return AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="http://test",
            headers=headers,
        )


@pytest_asyncio.fixture
async def env() -> AsyncGenerator[_Env, None]:
    """App over in-memory SQLite with one signed-in editor."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-integration-tests"
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    owner = await create_test_user("kb-sources@integration.test", UserRole.EDITOR)
    try:
        yield _Env(app=create_app(), owner=owner)
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


async def _carousel(owner: User, title: str) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    project_id = str(uuid4())
    async with get_session_maker()() as session:
        session.add(
            CarouselProjectModel(
                id=project_id,
                owner_id=str(owner.id),
                title=title,
                topic=title,
                audience="devs",
                niche="tech",
            )
        )
        await session.commit()
    return project_id


async def _source(
    project_id: str | None,
    title: str,
    *,
    minutes: int = 0,
    source_type: str = "note",
    content: str = "Some notes.",
    blog_post_id: str | None = None,
) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.source_comment import (
        ContentSourceModel,
    )

    source_id = str(uuid4())
    async with get_session_maker()() as session:
        session.add(
            ContentSourceModel(
                id=source_id,
                project_id=project_id,
                blog_post_id=blog_post_id,
                source_type=source_type,
                title=title,
                content=content,
                created_by="seed",
                created_at=_BASE_TIME + timedelta(minutes=minutes),
                updated_at=_BASE_TIME + timedelta(minutes=minutes),
            )
        )
        await session.commit()
    return source_id


@pytest.mark.integration
class TestCarouselSources:
    async def test_sources_are_listed_newest_first_with_their_carousel(
        self, env: _Env
    ) -> None:
        """Scenario: My carousels' sources are listed newest first with their carousel"""
        project_id = await _carousel(env.owner, "IA no trabalho")
        await _source(
            project_id,
            "Artigo da Nature",
            minutes=1,
            source_type="url",
            content="https://example.org/nature",
        )
        await _source(project_id, "Minhas notas", minutes=2)
        async with env.client_for(env.owner) as client:
            response = await client.get(_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert [item["title"] for item in body["items"]] == [
            "Minhas notas",
            "Artigo da Nature",
        ]
        note, url = body["items"]
        assert url["project_id"] == project_id
        assert url["project_title"] == "IA no trabalho"
        assert url["source_type"] == "url"
        assert url["url"] == "https://example.org/nature"
        assert note["url"] is None
        assert "content" not in note
        assert body["carousels"] == [
            {"project_id": project_id, "title": "IA no trabalho", "count": 2}
        ]

    async def test_the_list_paginates(self, env: _Env) -> None:
        """Scenario: The list paginates"""
        project_id = await _carousel(env.owner, "Paginado")
        for minute in range(3):
            await _source(project_id, f"Fonte {minute}", minutes=minute)
        async with env.client_for(env.owner) as client:
            response = await client.get(_URL, params={"limit": 2, "offset": 2})

        body = response.json()
        assert response.status_code == 200
        assert body["total"] == 3
        assert body["limit"] == 2
        assert body["offset"] == 2
        assert [item["title"] for item in body["items"]] == ["Fonte 0"]

    async def test_the_list_filters_by_carousel(self, env: _Env) -> None:
        """Scenario: The list can be filtered by carousel"""
        first = await _carousel(env.owner, "Primeiro")
        second = await _carousel(env.owner, "Segundo")
        await _source(first, "Do primeiro", minutes=1)
        await _source(second, "Do segundo A", minutes=2)
        await _source(second, "Do segundo B", minutes=3)
        async with env.client_for(env.owner) as client:
            response = await client.get(_URL, params={"project_id": first})

        body = response.json()
        assert [item["title"] for item in body["items"]] == ["Do primeiro"]
        assert body["total"] == 1
        assert sorted(
            (facet["title"], facet["count"]) for facet in body["carousels"]
        ) == [("Primeiro", 1), ("Segundo", 2)]

    async def test_another_owners_sources_are_never_listed(self, env: _Env) -> None:
        """Scenario: Another owner's sources are never listed"""
        other = await create_test_user("kb-sources-o@integration.test", UserRole.EDITOR)
        await _source(await _carousel(other, "Alheio"), "Fonte alheia")
        async with env.client_for(env.owner) as client:
            response = await client.get(_URL)

        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["carousels"] == []

    async def test_another_owners_carousel_filter_lists_nothing(
        self, env: _Env
    ) -> None:
        """Scenario: Another owner's sources are never listed"""
        other = await create_test_user("kb-sources-o2@integration.test", UserRole.EDITOR)
        project_id = await _carousel(other, "Alheio")
        await _source(project_id, "Fonte alheia")
        async with env.client_for(env.owner) as client:
            response = await client.get(_URL, params={"project_id": project_id})

        assert response.json()["items"] == []

    async def test_an_admin_sees_every_owners_sources(self, env: _Env) -> None:
        """Scenario: An admin sees every owner's sources"""
        admin = await create_test_user("kb-sources-a@integration.test", UserRole.ADMIN)
        await _source(await _carousel(env.owner, "Do editor"), "Fonte do editor")
        async with env.client_for(admin) as client:
            response = await client.get(_URL)

        assert [item["title"] for item in response.json()["items"]] == [
            "Fonte do editor"
        ]

    async def test_blog_post_sources_are_not_listed(self, env: _Env) -> None:
        """Scenario: Sources of a blog post are not carousel sources"""
        await _source(None, "Fonte do blog", blog_post_id=str(uuid4()))
        async with env.client_for(env.owner) as client:
            response = await client.get(_URL)

        assert response.json()["items"] == []

    async def test_anonymous_visitor_is_refused(self, env: _Env) -> None:
        """Scenario: An anonymous visitor cannot list carousel sources"""
        async with env.client_for(None) as client:
            response = await client.get(_URL)

        assert response.status_code == 401

    async def test_page_size_over_100_is_refused(self, env: _Env) -> None:
        """Scenario: A page size over 100 is refused"""
        async with env.client_for(env.owner) as client:
            response = await client.get(_URL, params={"limit": 101})

        assert response.status_code == 422
