"""Integration tests for carousel i18n and design API endpoints."""

from uuid import UUID

import pytest

from rag_backend.domain.models import CarouselProject, CarouselStatus, CarouselTheme


async def _set_carousel_public(project_id: str, *, is_public: bool = True) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

    session_maker = get_session_maker()
    async with session_maker() as session:
        model = await session.get(CarouselProjectModel, project_id)
        if model is not None:
            model.is_public = is_public
            await session.commit()


@pytest.fixture
def sample_carousel_with_blog():
    """Create a sample carousel project with bilingual blog."""
    project = CarouselProject(
        topic="Machine Learning Basics",
        audience="Beginners",
        niche="AI Education",
        theme=CarouselTheme.AI_COMPETITION,
    )
    project.blog_markdown = "# ML Basico\n\nConteudo em portugues."
    project.blog_translations = {
        "pt": "# ML Basico\n\nConteudo em portugues.",
        "en": "# ML Basics\n\nContent in English.",
    }
    project.set_title(title="Master ML in 7 Slides", subtitle="A beginner's guide")
    project.status = CarouselStatus.COMPLETED
    return project


@pytest.mark.integration
class TestCarouselBlogI18nEndpoints:
    """Integration tests for i18n blog endpoints."""

    @pytest.mark.asyncio
    async def test_get_carousel_blog_default(self, client):
        """Given carousel with blog, when GET /blog, then returns default blog."""
        payload = {
            "topic": "Blog Default Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_resp = await client.post("/api/carousels", json=payload)
        carousel_id = create_resp.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}/blog")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_carousel_blog_i18n_portuguese(self, client):
        """Given carousel with bilingual blog, when GET /blog/pt, then returns pt version."""
        payload = {
            "topic": "Blog PT Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_resp = await client.post("/api/carousels", json=payload)
        carousel_id = create_resp.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}/blog/pt")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_carousel_blog_i18n_invalid_language(self, client):
        """Given carousel, when GET /blog/invalid, then returns 422 validation error."""
        payload = {
            "topic": "Blog Invalid Lang",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_resp = await client.post("/api/carousels", json=payload)
        carousel_id = create_resp.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}/blog/xx")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_carousel_blog_i18n_not_found_project(self, client):
        """Given non-existent project, when GET /blog/pt, then returns 404."""
        response = await client.get(
            "/api/carousels/00000000-0000-0000-0000-000000000000/blog/pt"
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestCarouselDesignEndpoints:
    """Integration tests for design token endpoints."""

    @pytest.mark.asyncio
    async def test_get_carousel_design_not_found_project(self, client):
        """Given non-existent project, when GET /design, then returns 404."""
        response = await client.get(
            "/api/carousels/00000000-0000-0000-0000-000000000000/design"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_carousel_design_not_generated(self, client):
        """Given carousel without design tokens, when GET /design, then returns 404."""
        payload = {
            "topic": "Design Not Generated",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_resp = await client.post("/api/carousels", json=payload)
        carousel_id = create_resp.json()["id"]
        await _set_carousel_public(carousel_id)

        response = await client.get(f"/api/carousels/{carousel_id}/design")
        assert response.status_code == 404
        data = response.json()
        assert "not yet generated" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_carousel_design_translated_swipe_text(self, client):
        """Given a completed carousel, when GET /design?lang=en, then
        swipe_text is translated to English."""
        payload = {
            "topic": "Translated Swipe",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_resp = await client.post("/api/carousels", json=payload)
        carousel_id = create_resp.json()["id"]
        await _set_carousel_public(carousel_id)

        # Simulate completed project with design tokens
        from sqlalchemy.ext.asyncio import async_sessionmaker

        import rag_backend.infrastructure.database.config as db_config
        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )

        assert db_config.c_engine is not None
        Session = async_sessionmaker(db_config.c_engine, expire_on_commit=False)
        async with Session() as session:
            repo = PostgresCarouselRepository(session)
            proj = await repo.get_project_by_id(UUID(carousel_id))
            assert proj is not None
            proj.status = CarouselStatus.COMPLETED
            proj.design_tokens = {
                "colors": {
                    "primary": "#ff0000",
                    "accent": "#00ff00",
                    "bg": "#000000",
                    "text": "#ffffff",
                    "text_muted": "#888888",
                    "text_dim": "#666666",
                    "border": "#333333",
                    "glow": "#ff0000",
                },
                "typography": {
                    "font_family_heading": "Arial",
                    "font_family_body": "Arial",
                    "font_family_badge": "Courier",
                },
                "images": {"hero": "/hero", "slides": []},
                "layout": {
                    "badge_label": "Tech",
                    "swipe_text": "Deslize →",
                    "progress_segments": 7,
                },
            }
            await repo.update_project(proj)

        response = await client.get(f"/api/carousels/{carousel_id}/design?lang=en")
        assert response.status_code == 200
        data = response.json()
        assert data["layout"]["swipe_text"] == "Swipe →"


@pytest.mark.integration
class TestCarouselImageEndpoint:
    """Integration tests for carousel image serving endpoint."""

    @pytest.mark.asyncio
    async def test_get_carousel_image_not_found_project(self, client):
        """Given non-existent project, when GET /images/slide_1.jpg, then returns 404."""
        response = await client.get(
            "/api/carousels/00000000-0000-0000-0000-000000000000/images/slide_1.jpg"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_carousel_image_not_generated(self, client):
        """Given carousel without output, when GET /images/, then returns 404."""
        payload = {
            "topic": "Image Not Generated",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_resp = await client.post("/api/carousels", json=payload)
        carousel_id = create_resp.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}/images/slide_1.jpg")
        assert response.status_code == 404
        data = response.json()
        assert "not yet generated" in data["detail"]


@pytest.mark.integration
class TestCarouselSlidesEndpoint:
    """Integration tests for carousel slides endpoint."""

    @pytest.mark.asyncio
    async def test_get_carousel_slides_not_found_project(self, client):
        """Given non-existent project, when GET /slides, then returns 404."""
        response = await client.get(
            "/api/carousels/00000000-0000-0000-0000-000000000000/slides"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_carousel_slides_empty(self, client):
        """Given carousel with no slides, when GET /slides, then returns empty list."""
        payload = {
            "topic": "Slides Empty Test",
            "audience": "Everyone",
            "niche": "Tech",
        }
        create_resp = await client.post("/api/carousels", json=payload)
        carousel_id = create_resp.json()["id"]

        response = await client.get(f"/api/carousels/{carousel_id}/slides")
        assert response.status_code == 200
        data = response.json()
        assert data == []
