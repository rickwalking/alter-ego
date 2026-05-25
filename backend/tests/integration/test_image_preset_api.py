"""Integration tests for image_model/image_style preset validation.

Gherkin: tests/features/image_generation_provider.feature
"""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants import JWT_ALGORITHM, JWT_TYPE_AUTH
from rag_backend.domain.models import User, UserRole

TEST_SECRET = "test-secret-for-image-preset-integration-tests!"


@pytest.fixture(autouse=True)
def _test_settings():
    """Override secret keys for all tests in this module."""
    from rag_backend.infrastructure.config.settings import get_settings

    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-image-preset-tests"
    yield
    get_settings.cache_clear()


async def _create_user(email: str, role: UserRole) -> User:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.user_repository import PostgresUserRepository

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

    editor = await _create_user("editor@example.com", UserRole.EDITOR)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=_auth_headers(editor),
    ) as ac:
        yield ac

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


@pytest.mark.integration
class TestImagePresetValidation:
    """API-level 422 validation for image_model/image_style combos."""

    @pytest.mark.asyncio
    async def test_default_preset_is_accepted(self, client):
        """Scenario: Default provider + style when caller omits both fields."""
        payload = {
            "topic": "T",
            "audience": "A",
            "niche": "N",
        }
        response = await client.post("/api/carousels", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body["image_model"] == "gemini"
        assert body["image_style"] == "comic_neon"

    @pytest.mark.asyncio
    async def test_openai_hyperreal_preset_accepted(self, client):
        """Scenario: Caller picks OpenAI hyperreal preset."""
        payload = {
            "topic": "T",
            "audience": "A",
            "niche": "N",
            "image_model": "openai",
            "image_style": "hyperreal",
        }
        response = await client.post("/api/carousels", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body["image_model"] == "openai"
        assert body["image_style"] == "hyperreal"

    @pytest.mark.asyncio
    async def test_invalid_model_rejected(self, client):
        """Scenario: Invalid model rejected at API layer."""
        payload = {
            "topic": "T",
            "audience": "A",
            "niche": "N",
            "image_model": "dalle-3",
            "image_style": "comic_neon",
        }
        response = await client.post("/api/carousels", json=payload)
        assert response.status_code == 422
        assert "image_model" in response.text

    @pytest.mark.asyncio
    async def test_invalid_style_rejected(self, client):
        """Scenario: Invalid style rejected at API layer."""
        payload = {
            "topic": "T",
            "audience": "A",
            "niche": "N",
            "image_model": "gemini",
            "image_style": "ukiyo_e",
        }
        response = await client.post("/api/carousels", json=payload)
        assert response.status_code == 422
        assert "image_style" in response.text

    @pytest.mark.asyncio
    async def test_incompatible_combo_rejected(self, client):
        """Scenario: Incompatible combo (gemini, cinematic) rejected."""
        payload = {
            "topic": "T",
            "audience": "A",
            "niche": "N",
            "image_model": "gemini",
            "image_style": "cinematic",
        }
        response = await client.post("/api/carousels", json=payload)
        assert response.status_code == 422
        assert "not supported" in response.text
