"""Integration tests for Phase 4 quality and polish APIs.

Feature: phase4_quality_polish.feature
"""

import os
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.models import User, UserRole

TEST_SECRET = "test-secret-for-phase4-quality-tests!!"


@pytest.fixture(autouse=True)
def _test_settings():
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-phase4-tests"
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client():
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


async def _create_user(email: str, role: UserRole) -> User:
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
    }
    return jwt.encode(payload, TEST_SECRET, algorithm=JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_seo_analyze_endpoint(client: AsyncClient) -> None:
    # Scenario: SEO analysis returns score and issues
    editor = await _create_user(f"editor-{uuid4().hex[:6]}@test.com", UserRole.EDITOR)
    token = _token(editor)

    create_resp = await client.post(
        "/api/blog-posts",
        json={"title": "Test Post", "slug": f"test-{uuid4().hex[:8]}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/blog-posts/{post_id}/seo-analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "issues" in data


@pytest.mark.asyncio
async def test_editorial_analytics_endpoint(client: AsyncClient) -> None:
    # Scenario: Editorial analytics returns velocity metrics
    editor = await _create_user(f"editor-{uuid4().hex[:6]}@test.com", UserRole.EDITOR)
    token = _token(editor)

    response = await client.get(
        "/api/editorial-analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "content_velocity_per_week" in data["summary"]
    assert "quality_score_average" in data["summary"]
