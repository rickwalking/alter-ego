"""Unit tests for the AE-0308 creation-time image-provider key guard.

Gherkin: tests/features/carousel_image_provider_reroute_ae0308.feature
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from rag_backend.api.dependencies.feature_flags import (
    require_image_provider_configured,
)
from rag_backend.api.schemas.carousel import CarouselProjectCreate
from rag_backend.domain.constants import (
    IMAGE_MODEL_GEMINI,
    IMAGE_MODEL_OPENAI,
    IMAGE_STYLE_COMIC_NEON,
)
from rag_backend.infrastructure.config.settings import Settings, get_settings

_ENV_PRODUCTION = "production"
_ENV_DEVELOPMENT = "development"
_GUARD_ERROR_PREFIX = "image_provider_unconfigured"


def _settings(environment: str, openai_key: str) -> Settings:
    return Settings(
        _env_file=None,
        secret_key=SecretStr("unit-test-secret-key"),
        anon_secret_key=SecretStr("unit-test-anon-secret"),
        environment=environment,
        openai_api_key=SecretStr(openai_key),
        gemini_api_key=SecretStr(""),
    )


def _create_body() -> CarouselProjectCreate:
    return CarouselProjectCreate(
        topic="T",
        audience="A",
        niche="N",
        image_model=IMAGE_MODEL_OPENAI,
        image_style=IMAGE_STYLE_COMIC_NEON,
    )


@pytest.mark.unit
class TestImageProviderApiKeyMapping:
    """Settings.image_provider_api_key is the single provider→key map."""

    def test_openai_maps_to_openai_key(self) -> None:
        settings = _settings(_ENV_DEVELOPMENT, openai_key="sk-test")
        key = settings.image_provider_api_key(IMAGE_MODEL_OPENAI)
        assert key is not None
        assert key.get_secret_value() == "sk-test"

    def test_gemini_maps_to_gemini_key(self) -> None:
        settings = _settings(_ENV_DEVELOPMENT, openai_key="sk-test")
        key = settings.image_provider_api_key(IMAGE_MODEL_GEMINI)
        assert key is not None
        assert key.get_secret_value() == ""

    def test_unknown_provider_returns_none(self) -> None:
        settings = _settings(_ENV_DEVELOPMENT, openai_key="sk-test")
        assert settings.image_provider_api_key("dalle-3") is None


@pytest.mark.unit
class TestRequireImageProviderConfigured:
    """Scenario: Creation fails fast when the requested provider has no API key."""

    def test_production_missing_key_raises_422(self) -> None:
        settings = _settings(_ENV_PRODUCTION, openai_key="")
        with pytest.raises(HTTPException) as exc_info:
            require_image_provider_configured(_create_body(), settings)
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail.startswith(_GUARD_ERROR_PREFIX)
        assert IMAGE_MODEL_OPENAI in exc_info.value.detail

    def test_production_present_key_passes(self) -> None:
        settings = _settings(_ENV_PRODUCTION, openai_key="sk-live")
        assert require_image_provider_configured(_create_body(), settings) is None

    def test_development_missing_key_is_tolerated(self) -> None:
        # Mirrors the AE-0215 startup-guard policy: dev/test tolerate a
        # missing key so local runs and stubbed tests keep working.
        settings = _settings(_ENV_DEVELOPMENT, openai_key="")
        assert require_image_provider_configured(_create_body(), settings) is None


@pytest.mark.unit
class TestGuardOverHttp:
    """Scenario: the API responds 422 before any workflow phase runs."""

    def _app(self, settings: Settings) -> FastAPI:
        app = FastAPI()

        @app.post(
            "/projects",
            dependencies=[Depends(require_image_provider_configured)],
        )
        async def create(request: CarouselProjectCreate) -> dict[str, str]:
            return {"status": "created"}

        app.dependency_overrides[get_settings] = lambda: settings
        return app

    @pytest.mark.asyncio
    async def test_unconfigured_provider_returns_422_over_http(self) -> None:
        app = self._app(_settings(_ENV_PRODUCTION, openai_key=""))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/projects", json=_create_body().model_dump())
        assert response.status_code == 422
        assert _GUARD_ERROR_PREFIX in response.text

    @pytest.mark.asyncio
    async def test_configured_provider_creates_over_http(self) -> None:
        app = self._app(_settings(_ENV_PRODUCTION, openai_key="sk-live"))
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/projects", json=_create_body().model_dump())
        assert response.status_code == 200
        assert response.json() == {"status": "created"}
