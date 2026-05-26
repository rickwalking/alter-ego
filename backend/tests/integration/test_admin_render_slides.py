"""Integration tests for admin re-render slides endpoint.

Feature: Admin Re-render Missing Slides
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.models import CarouselProject, CarouselStatus, User, UserRole

# Use deterministic test secret so token generation matches server
TEST_SECRET = "test-secret-for-admin-tests-32chars!!"


@pytest.fixture(autouse=True)
def _test_settings():
    """Override secret keys for all tests in this module."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-admin-tests"
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client():
    """Create async test client with in-memory SQLite."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
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
def mock_carousel_agent():
    """Create a mock carousel agent for render-slides tests."""
    agent = AsyncMock()
    agent.re_render_slides = AsyncMock()
    return agent


async def _create_user(client, email: str, role: UserRole) -> User:

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresUserRepository(session)
        user = User(
            email=email,
            full_name=email.split("@")[0].title(),
            role=role,
            hashed_password="not-used-in-tests",
        )
        created = await repo.create(user)
        await session.commit()
        return created


def _token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": JWT_TYPE_AUTH,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm=JWT_ALGORITHM)


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


async def _create_carousel(
    client, output_dir: str | None = "/tmp/test-output"
) -> CarouselProject:
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresCarouselRepository(session)
        project = CarouselProject(
            topic="Test",
            audience="Everyone",
            niche="Tech",
            output_dir=output_dir,
        )
        project.status = CarouselStatus.COMPLETED
        created = await repo.create_project(project)
        await session.commit()
        return created


@pytest.mark.integration
class TestAdminRenderSlides:
    """Integration tests for POST /api/admin/carousels/render-slides."""

    @pytest.mark.asyncio
    async def test_re_renders_missing_slides(
        self,
        client,
        mock_carousel_agent,
    ):
        admin = await _create_user(client, "admin@test.com", UserRole.ADMIN)
        await _create_carousel(client)

        with patch(
            "rag_backend.infrastructure.container.get_container"
        ) as mock_container:
            from rag_backend.infrastructure.container import Container

            test_container = Container()
            test_container.carousel_agent.override(mock_carousel_agent)
            mock_container.return_value = test_container

            response = await client.post(
                "/api/admin/carousels/render-slides",
                headers=_auth_headers(admin),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["skipped"] == 0
        assert data["updated"] == 1

    @pytest.mark.asyncio
    async def test_returns_403_for_editor(
        self,
        client,
    ):
        editor = await _create_user(client, "editor@test.com", UserRole.EDITOR)
        response = await client.post(
            "/api/admin/carousels/render-slides",
            headers=_auth_headers(editor),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_401_for_unauthenticated(
        self,
        client,
    ):
        response = await client.post("/api/admin/carousels/render-slides")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reports_failures(
        self,
        client,
        mock_carousel_agent,
    ):
        admin = await _create_user(client, "admin2@test.com", UserRole.ADMIN)
        await _create_carousel(client)

        mock_carousel_agent.re_render_slides = AsyncMock(
            side_effect=ValueError("playwright error")
        )

        with patch(
            "rag_backend.infrastructure.container.get_container"
        ) as mock_container:
            from rag_backend.infrastructure.container import Container

            test_container = Container()
            test_container.carousel_agent.override(mock_carousel_agent)
            mock_container.return_value = test_container

            response = await client.post(
                "/api/admin/carousels/render-slides",
                headers=_auth_headers(admin),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["updated"] == 0
        assert data["failed"] == 1
        assert any("playwright" in e for e in data["errors"])
