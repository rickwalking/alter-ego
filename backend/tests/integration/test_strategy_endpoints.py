"""Integration tests for strategy API endpoints.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.infrastructure.container import get_container


async def _create_project(status: CarouselStatus) -> CarouselProject:
    """Persist a carousel project with the given status into the test DB."""
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
            output_dir="/tmp/test-output",
        )
        project.status = status
        created = await repo.create_project(project)
        await session.commit()
        return created


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

    async def test_list_returns_eight_strategies(self, client: AsyncClient):
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

    async def test_non_completed_project_returns_409(self, client: AsyncClient):
        # Scenario: a valid strategy on a not-yet-completed project conflicts.
        registry = get_container().strategy_registry()
        valid_name = registry.list()[0]["name"]
        project = await _create_project(CarouselStatus.DRAFTING)
        response = await client.put(
            f"/api/carousels/{project.id}/strategy",
            params={"name": valid_name},
        )
        assert response.status_code == 409

    async def test_valid_strategy_on_completed_project_returns_200(
        self, client: AsyncClient
    ):
        # Scenario: Active strategy applied and re-render triggered.
        registry = get_container().strategy_registry()
        valid_name = registry.list()[0]["name"]
        project = await _create_project(CarouselStatus.COMPLETED)

        mock_refinement = AsyncMock()
        mock_refinement.re_render_slides = AsyncMock()
        with patch(
            "rag_backend.infrastructure.container.get_container"
        ) as mock_container:
            from rag_backend.infrastructure.container import Container

            test_container = Container()
            test_container.carousel_refinement.override(mock_refinement)
            mock_container.return_value = test_container

            response = await client.put(
                f"/api/carousels/{project.id}/strategy",
                params={"name": valid_name},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy"] == valid_name
        assert data["project_id"] == str(project.id)
        mock_refinement.re_render_slides.assert_awaited_once()
