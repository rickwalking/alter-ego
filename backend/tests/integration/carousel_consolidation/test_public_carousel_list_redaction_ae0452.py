"""Public carousel feed: finished carousels only, no private fields.

Gherkin: tests/features/public_carousel_list_redaction_ae0452.feature
"""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import CarouselSlide, CarouselStatus
from rag_backend.domain.models.user import UserRole
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    set_carousel_status,
)

DRAFT = "# Hidden draft\n\nUnpublished body"
PRIVATE_FIELDS = (
    "blog_markdown",
    "blog_translations",
    "caption",
    "linkedin_post_pt",
    "linkedin_post_en",
    "error_message",
    "output_dir",
    "pdf_path",
    "pdf_path_en",
    "custom_visual_details",
    "pov_thesis",
    "pov_personal_proof",
    "hook_asset_id",
    "persona_id",
)
SEEDED_PRIVATE = {
    "error_message": "Traceback: /srv/app/secret.py",
    "custom_visual_details": "Owner-only scene notes",
    "pov_thesis": "Owner thesis",
    "pov_personal_proof": "Owner personal proof",
    "persona_id": "11111111-1111-4111-8111-111111111111",
    "hook_asset_id": "22222222-2222-4222-8222-222222222222",
}
SLIDE_IMAGE_PATH = "/tmp/test-carousel-output/slide_1.jpg"


async def _seed_private_fields(project_id: str) -> None:
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        for field, value in SEEDED_PRIVATE.items():
            setattr(model, field, value)
        await PostgresCarouselRepository(session).create_slide(
            CarouselSlide(
                project_id=UUID(project_id),
                slide_number=1,
                slide_type="content",
                heading="Heading",
                body="Body",
                image_path=SLIDE_IMAGE_PATH,
            )
        )
        await session.commit()


async def _public_carousel(status: CarouselStatus) -> str:
    owner = await create_user("owner@example.com", UserRole.EDITOR)
    project_id = await create_carousel(owner, is_public=True, blog_markdown=DRAFT)
    await set_carousel_status(project_id, status)
    return project_id


def _item(payload: dict[str, object], project_id: str) -> dict[str, object]:
    items = payload["items"]
    assert isinstance(items, list)
    matches = [item for item in items if item["id"] == project_id]
    assert len(matches) == 1
    found = matches[0]
    assert isinstance(found, dict)
    return found


@pytest.mark.integration
class TestAnonymousFeedStatus:
    """The anonymous feed lists finished carousels only."""

    async def test_generating_public_carousel_is_not_listed(
        self, client: AsyncClient
    ) -> None:
        # Scenario: An anonymous feed never lists an unfinished carousel
        await _public_carousel(CarouselStatus.GENERATING_IMAGES)

        response = await client.get("/api/carousels?limit=100")

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0


@pytest.mark.integration
class TestPublicFeedRedaction:
    """A public feed item carries no owner-only data."""

    async def test_anonymous_item_has_no_private_fields(
        self, client: AsyncClient
    ) -> None:
        # Scenario: An anonymous feed item carries no private fields
        project_id = await _public_carousel(CarouselStatus.COMPLETED)
        await _seed_private_fields(project_id)

        response = await client.get("/api/carousels?public=true&limit=100")

        assert response.status_code == 200
        item = _item(response.json(), project_id)
        assert item["topic"] == "Consolidation Test"
        assert item["language"] == "pt-BR"
        for field in PRIVATE_FIELDS:
            assert item[field] is None, field
        assert item["research_sources"] == []
        assert item["slides"] == []
        assert "Hidden draft" not in response.text
        assert "/tmp/test-carousel-output" not in response.text
        for value in SEEDED_PRIVATE.values():
            assert value not in response.text

    async def test_signed_in_editor_public_feed_is_redacted(
        self, client: AsyncClient
    ) -> None:
        # Scenario: A signed-in non-admin browsing the public feed gets the same redacted items
        project_id = await _public_carousel(CarouselStatus.COMPLETED)
        viewer = await create_user("viewer@example.com", UserRole.EDITOR)

        response = await client.get(
            "/api/carousels?public=true&limit=100", headers=auth_header(viewer)
        )

        assert response.status_code == 200
        assert _item(response.json(), project_id)["blog_markdown"] is None

    async def test_admin_list_keeps_full_project(self, client: AsyncClient) -> None:
        # Scenario: An admin listing carousels still sees the full project
        project_id = await _public_carousel(CarouselStatus.COMPLETED)
        admin = await create_user("admin@example.com", UserRole.ADMIN)

        response = await client.get(
            "/api/carousels?limit=100", headers=auth_header(admin)
        )

        assert response.status_code == 200
        item = _item(response.json(), project_id)
        assert item["blog_markdown"] == DRAFT
        assert item["output_dir"] == "/tmp/test-carousel-output"

    async def test_admin_public_feed_keeps_full_project(
        self, client: AsyncClient
    ) -> None:
        # Scenario: An admin browsing the public feed still sees the full project
        project_id = await _public_carousel(CarouselStatus.COMPLETED)
        await _seed_private_fields(project_id)
        admin = await create_user("admin@example.com", UserRole.ADMIN)

        response = await client.get(
            "/api/carousels?public=true&limit=100", headers=auth_header(admin)
        )

        assert response.status_code == 200
        item = _item(response.json(), project_id)
        assert item["blog_markdown"] == DRAFT
        assert item["pov_thesis"] == "Owner thesis"
        assert item["error_message"] == SEEDED_PRIVATE["error_message"]


@pytest.mark.integration
class TestSignedInPublicFeedStatus:
    """A signed-in non-admin browsing the public feed sees finished carousels only."""

    @pytest.mark.parametrize("query", ["", "&status=failed"])
    async def test_editor_public_feed_skips_unfinished(
        self, client: AsyncClient, query: str
    ) -> None:
        # Scenario: A signed-in editor browsing the public feed never lists an unfinished carousel
        await _public_carousel(CarouselStatus.FAILED)
        viewer = await create_user("viewer@example.com", UserRole.EDITOR)

        response = await client.get(
            f"/api/carousels?public=true&limit=100{query}",
            headers=auth_header(viewer),
        )

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    async def test_admin_status_filter_is_kept(self, client: AsyncClient) -> None:
        # Scenario: An admin listing carousels still sees the full project
        project_id = await _public_carousel(CarouselStatus.FAILED)
        admin = await create_user("admin@example.com", UserRole.ADMIN)

        response = await client.get(
            "/api/carousels?status=failed&limit=100", headers=auth_header(admin)
        )

        assert response.status_code == 200
        assert _item(response.json(), project_id)["status"] == "failed"
