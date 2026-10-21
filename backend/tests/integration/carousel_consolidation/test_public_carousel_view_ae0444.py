"""Public carousel viewer + feed projection.

Gherkin: tests/features/public_carousel_view_ae0444.feature
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    CarouselTheme,
)

PROJECT_ID = UUID("0f8fad5b-d9cb-469f-a165-70867728950e")


def _write_slide(output_dir: Path, subdir: str, number: int) -> None:
    path = output_dir / subdir / f"slide_{number}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"jpeg")


async def _seed(
    *,
    output_dir: Path,
    is_public: bool = True,
    status: CarouselStatus = CarouselStatus.COMPLETED,
    language: str = "pt-BR",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    design_tokens: dict[str, object] | None = None,
    pt_slides: tuple[int, ...] = (1, 2),
    en_slides: tuple[int, ...] = (1,),
) -> str:
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    for number in pt_slides:
        _write_slide(output_dir, "pt", number)
    for number in en_slides:
        _write_slide(output_dir, "en", number)

    project = CarouselProject(
        topic="Public viewer",
        audience="Devs",
        niche="AI",
        title="Título público",
        title_en="Public title",
        subtitle="Subtítulo",
        language=language,
        theme=CarouselTheme.AI_COMPETITION,
        is_public=is_public,
        status=status,
        output_dir=str(output_dir),
        design_tokens=design_tokens,
        created_at=created_at or datetime(2026, 10, 20, 11, 40, 1),
        updated_at=updated_at or datetime(2026, 10, 20, 11, 40, 1),
    )
    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresCarouselRepository(session)
        created = await repo.create_project(project)
        for number in sorted(set(pt_slides) | set(en_slides)):
            await repo.create_slide(
                _slide(created.id, number),
            )
        await session.commit()
        return str(created.id)


def _slide(project_id: UUID, number: int) -> CarouselSlide:
    return CarouselSlide(
        project_id=project_id,
        slide_number=number,
        slide_type="content",
        heading=f"Heading {number}",
        body="Body",
    )


@pytest.mark.integration
class TestPublicCarouselEndpoint:
    """Scenarios: only public + completed carousels expose a viewer projection."""

    async def test_public_completed_carousel_is_readable(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        project_id = await _seed(output_dir=tmp_path / "carousel")

        response = await client.get(f"/api/carousels/{project_id}/public")

        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "Título público"
        assert payload["title_en"] == "Public title"
        assert payload["language"] == "pt-BR"
        assert payload["slide_count"] == 2
        assert payload["available_languages"] == ["pt", "en"]
        assert payload["slides_by_language"]["pt"][0] == {
            "slide_number": 1,
            "heading": "Heading 1",
            "image_url": f"/api/carousels/{project_id}/slide-images/pt/slide_1.jpg",
        }
        assert payload["slides_by_language"]["en"][0]["image_url"].endswith(
            "/slide-images/en/slide_1.jpg"
        )
        assert payload["cover_url"].endswith("/slide-images/pt/slide_1.jpg")
        assert "image_path" not in response.text
        assert "/preview/" not in response.text

    async def test_private_carousel_is_404(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        project_id = await _seed(output_dir=tmp_path / "carousel", is_public=False)

        response = await client.get(f"/api/carousels/{project_id}/public")

        assert response.status_code == 404

    async def test_public_but_not_completed_is_404(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        project_id = await _seed(
            output_dir=tmp_path / "carousel",
            status=CarouselStatus.PENDING,
        )

        response = await client.get(f"/api/carousels/{project_id}/public")

        assert response.status_code == 404

    async def test_unknown_carousel_is_404(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/carousels/{PROJECT_ID}/public")

        assert response.status_code == 404

    async def test_stored_preview_urls_are_mapped_to_public_urls(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        project_id = await _seed(
            output_dir=tmp_path / "carousel",
            design_tokens={
                "images": {
                    "hero": f"/api/carousels/{PROJECT_ID}/preview/images/slide_1.jpg",
                    "rendered_slides_pt": [
                        f"/api/carousels/{PROJECT_ID}/preview/images/slide_1.jpg?lang=pt"
                    ],
                    "rendered_slides_en": [
                        f"/api/carousels/{PROJECT_ID}/preview/images/slide_1.jpg?lang=en"
                    ],
                }
            },
        )

        response = await client.get(f"/api/carousels/{project_id}/public")

        assert response.status_code == 200
        assert "/preview/" not in response.text
        assert "/images/slide_1.jpg" in response.text


@pytest.mark.integration
class TestPublicCarouselFeed:
    """Scenarios: the public feed is newest-first and reports language."""

    async def test_feed_reports_language(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        await _seed(output_dir=tmp_path / "carousel", language="pt-BR")

        response = await client.get(
            "/api/carousels?public=true&status=completed&limit=100"
        )

        assert response.status_code == 200
        assert response.json()["items"][0]["language"] == "pt-BR"

    async def test_sort_created_at_overrides_updated_at_order(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        older_created = await _seed(
            output_dir=tmp_path / "older",
            created_at=datetime(2026, 10, 1, 12, 0, 0),
            updated_at=datetime(2026, 10, 20, 12, 0, 0),
        )
        newer_created = await _seed(
            output_dir=tmp_path / "newer",
            created_at=datetime(2026, 10, 19, 12, 0, 0),
            updated_at=datetime(2026, 10, 2, 12, 0, 0),
        )

        by_created = await client.get(
            "/api/carousels?public=true&status=completed&sort=created_at&limit=100"
        )
        by_updated = await client.get(
            "/api/carousels?public=true&status=completed&limit=100"
        )

        assert by_created.status_code == 200
        assert [item["id"] for item in by_created.json()["items"]][:2] == [
            newer_created,
            older_created,
        ]
        assert [item["id"] for item in by_updated.json()["items"]][:2] == [
            older_created,
            newer_created,
        ]
