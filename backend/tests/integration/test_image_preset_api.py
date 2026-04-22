"""Integration tests for image_model/image_style preset validation.

Gherkin: tests/features/image_generation_provider.feature
"""

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.api.app import create_app


@pytest.fixture
async def client():
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
