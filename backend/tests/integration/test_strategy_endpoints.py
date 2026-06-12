"""Integration tests for strategy API endpoints.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

import pytest
from httpx import AsyncClient

from rag_backend.infrastructure.container import get_container


@pytest.mark.integration
class TestStrategyListEndpoint:
    """Scenario: List available strategies."""

    async def test_list_strategies_returns_array(self, client: AsyncClient):
        response = await client.get("/api/carousels/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert len(data["strategies"]) > 0

    async def test_each_strategy_has_name_and_display_name(self, client: AsyncClient):
        response = await client.get("/api/carousels/strategies")
        data = response.json()
        for strategy in data["strategies"]:
            assert "name" in strategy
            assert "display_name" in strategy

    async def test_list_returns_seven_strategies(self, client: AsyncClient):
        response = await client.get("/api/carousels/strategies")
        data = response.json()
        assert len(data["strategies"]) == 8


@pytest.mark.integration
class TestStrategyApplyEndpoint:
    """Scenario: Apply a strategy to a carousel project."""

    async def test_invalid_strategy_returns_422(self, client: AsyncClient):
        response = await client.put(
            "/api/carousels/00000000-0000-0000-0000-000000000001/strategy",
            params={"name": "nonexistent"},
        )
        assert response.status_code == 422

    async def test_nonexistent_project_returns_404(self, client: AsyncClient):
        registry = get_container().strategy_registry()
        valid_name = registry.list()[0]["name"]
        response = await client.put(
            "/api/carousels/00000000-0000-0000-0000-000000000001/strategy",
            params={"name": valid_name},
        )
        assert response.status_code == 404
