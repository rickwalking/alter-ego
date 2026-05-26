"""Unit tests for feature flag dependencies."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from rag_backend.api.dependencies.feature_flags import require_feature
from rag_backend.domain.constants.feature_flags import (
    ERR_FEATURE_DISABLED,
    FLAG_QUALITY_CHECKS,
)
from rag_backend.infrastructure.config.settings import Settings, get_settings


@pytest.fixture
def app_with_flag(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    app = FastAPI()

    @app.get("/gated", dependencies=[Depends(require_feature(FLAG_QUALITY_CHECKS))])
    async def gated() -> dict[str, str]:
        return {"status": "ok"}

    return app


class TestFeatureFlags:
    # Scenario: DEPLOY-003 Feature flag disables quality endpoints
    @pytest.mark.asyncio
    async def test_disabled_flag_returns_503(
        self, app_with_flag: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        get_settings.cache_clear()
        monkeypatch.setenv("FEATURE_FLAG_QUALITY_CHECKS", "false")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-feature-flags!!")
        monkeypatch.setenv("ANON_SECRET_KEY", "test-anon-secret-for-feature-flags!")

        transport = ASGITransport(app=app_with_flag)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/gated")

        assert response.status_code == 503
        assert response.json()["detail"] == ERR_FEATURE_DISABLED
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_enabled_flag_allows_request(
        self, app_with_flag: FastAPI, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        get_settings.cache_clear()
        monkeypatch.setenv("FEATURE_FLAG_QUALITY_CHECKS", "true")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-feature-flags!!")
        monkeypatch.setenv("ANON_SECRET_KEY", "test-anon-secret-for-feature-flags!")

        transport = ASGITransport(app=app_with_flag)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/gated")

        assert response.status_code == 200
        get_settings.cache_clear()

    def test_settings_feature_flags_map(self, monkeypatch: pytest.MonkeyPatch) -> None:
        get_settings.cache_clear()
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-feature-flags!!")
        monkeypatch.setenv("ANON_SECRET_KEY", "test-anon-secret-for-feature-flags!")
        monkeypatch.setenv("FEATURE_FLAG_EDITORIAL_WORKFLOW", "false")

        settings = Settings()
        assert settings.feature_flags["editorial_workflow"] is False
        get_settings.cache_clear()
