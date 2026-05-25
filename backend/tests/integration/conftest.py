"""Shared fixtures for integration tests."""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.models import User, UserRole

TEST_SECRET = "test-secret-for-integration-tests!!"


@pytest.fixture(autouse=True)
def integration_test_settings() -> None:
    """Override secret keys for integration tests."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-integration-tests"
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client():
    """Async test client with in-memory SQLite and editor JWT auth."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db_config.c_engine = engine

    user = await create_test_user("editor@integration.test", UserRole.EDITOR)
    headers = auth_headers_for(user)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as ac:
        yield ac

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def create_test_user(email: str, role: UserRole) -> User:
    """Persist a user for integration tests."""
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


def auth_token_for(user: User) -> str:
    """Build a JWT for the given user."""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": JWT_TYPE_AUTH,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, TEST_SECRET, algorithm=JWT_ALGORITHM)


def auth_headers_for(user: User) -> dict[str, str]:
    """Build Authorization headers for the given user."""
    return {"Authorization": f"Bearer {auth_token_for(user)}"}
