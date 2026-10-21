"""Public carousel 404 parity (AE-0446, ADR-0013).

Gherkin: tests/features/public_carousel_404_parity_ae0446.feature
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient, Response

from rag_backend.domain.models import CarouselStatus
from tests.integration.carousel_consolidation.test_public_carousel_view_ae0444 import (
    PROJECT_ID,
    _seed,
)

_SLIDE_IMAGE = "slide-images/pt/slide_1.jpg"


def _viewer(project_id: object) -> str:
    return f"/api/carousels/{project_id}/public"


def _slide_image(project_id: object) -> str:
    return f"/api/carousels/{project_id}/{_SLIDE_IMAGE}"


async def _clear_output_dir(project_id: str) -> None:
    """Make the seeded project look unrendered (no output directory)."""
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models import CarouselProjectModel

    async with get_session_maker()() as session:
        project = await session.get(CarouselProjectModel, project_id)
        assert project is not None
        project.output_dir = None
        await session.commit()


def _assert_same_404(hidden: Response, unknown: Response) -> None:
    assert hidden.status_code == 404
    assert unknown.status_code == 404
    assert hidden.json() == unknown.json()


@pytest.mark.integration
class TestPublicCarousel404Parity:
    # Scenario: The viewer answers a private and an unknown carousel identically
    async def test_viewer_private_matches_unknown(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        project_id = await _seed(output_dir=tmp_path / "carousel", is_public=False)

        private = await client.get(_viewer(project_id))
        unknown = await client.get(_viewer(PROJECT_ID))

        _assert_same_404(private, unknown)

    # Scenario: The viewer answers an unfinished public carousel like an unknown one
    async def test_viewer_unfinished_matches_unknown(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        project_id = await _seed(
            output_dir=tmp_path / "carousel", status=CarouselStatus.PENDING
        )

        unfinished = await client.get(_viewer(project_id))
        unknown = await client.get(_viewer(PROJECT_ID))

        _assert_same_404(unfinished, unknown)

    # Scenario: The public slide image route answers a private and an unknown
    # carousel identically
    async def test_slide_image_private_matches_unknown(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        project_id = await _seed(output_dir=tmp_path / "carousel", is_public=False)

        private = await client.get(_slide_image(project_id))
        unknown = await client.get(_slide_image(PROJECT_ID))

        _assert_same_404(private, unknown)

    # Scenario: A private carousel that is not rendered yet answers like an unknown id
    async def test_unrendered_private_image_matches_unknown(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        project_id = await _seed(
            output_dir=tmp_path / "carousel", is_public=False, pt_slides=()
        )
        await _clear_output_dir(project_id)
        image = "images/slide_1.jpg"

        private = await client.get(f"/api/carousels/{project_id}/{image}")
        unknown = await client.get(f"/api/carousels/{PROJECT_ID}/{image}")

        _assert_same_404(private, unknown)
