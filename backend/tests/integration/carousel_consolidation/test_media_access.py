"""Carousel consolidation integration tests.

Feature: carousel_pipeline_consolidation.feature
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import (
    CarouselProject,
    CarouselTheme,
    UserRole,
)
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
)


class TestMediaAccessControl:
    """Scenario: Non-owner editor cannot access protected media routes."""

    @pytest.mark.asyncio
    async def test_non_owner_cannot_download_pdf(self, client: AsyncClient) -> None:
        owner = await create_user("pdf-owner@example.com", UserRole.EDITOR)
        other = await create_user("pdf-other@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        response = await client.get(
            f"/api/carousels/{project_id}/pdf",
            headers=auth_header(other),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_owner_cannot_list_slides(self, client: AsyncClient) -> None:
        owner = await create_user("slides-owner@example.com", UserRole.EDITOR)
        other = await create_user("slides-other@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        response = await client.get(
            f"/api/carousels/{project_id}/slides",
            headers=auth_header(other),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_owner_cannot_download_files(self, client: AsyncClient) -> None:
        owner = await create_user("dl-owner@example.com", UserRole.EDITOR)
        other = await create_user("dl-other@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        response = await client.get(
            f"/api/carousels/{project_id}/download",
            headers=auth_header(other),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_owner_cannot_generate_caption(self, client: AsyncClient) -> None:
        owner = await create_user("cap-owner@example.com", UserRole.EDITOR)
        other = await create_user("cap-other@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        response = await client.post(
            f"/api/carousels/{project_id}/caption",
            headers=auth_header(other),
        )
        assert response.status_code == 403


class TestPdfPathConfinement:
    """Scenario: PDF paths outside output_dir are rejected."""

    @pytest.mark.asyncio
    async def test_pdf_outside_output_dir_returns_not_found(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        editor = await create_user("pdf-path@example.com", UserRole.EDITOR)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        outside_pdf = tmp_path / "outside.pdf"
        outside_pdf.write_text("pdf", encoding="utf-8")

        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = PostgresCarouselRepository(session)
            project = CarouselProject(
                topic="PDF confinement",
                audience="Devs",
                niche="AI",
                theme=CarouselTheme.AI_COMPETITION,
                owner_id=str(editor.id),
                output_dir=str(output_dir),
                pdf_path=str(outside_pdf),
            )
            created = await repo.create_project(project)
            await session.commit()
            project_id = str(created.id)

        response = await client.get(
            f"/api/carousels/{project_id}/pdf",
            headers=auth_header(editor),
        )
        assert response.status_code == 404


class TestDownloadResponse:
    """Scenario: Download response does not expose absolute output_dir."""

    @pytest.mark.asyncio
    async def test_download_response_omits_output_dir(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        editor = await create_user("download@example.com", UserRole.EDITOR)
        output_dir = tmp_path / "carousel-output"
        output_dir.mkdir()
        (output_dir / "slide_1.jpg").write_bytes(b"jpeg")

        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = PostgresCarouselRepository(session)
            project = CarouselProject(
                topic="Download test",
                audience="Devs",
                niche="AI",
                theme=CarouselTheme.AI_COMPETITION,
                owner_id=str(editor.id),
                output_dir=str(output_dir),
            )
            created = await repo.create_project(project)
            await session.commit()
            project_id = str(created.id)

        response = await client.get(
            f"/api/carousels/{project_id}/download",
            headers=auth_header(editor),
        )
        assert response.status_code == 200
        payload = response.json()
        assert "output_dir" not in payload
        assert "slide_1.jpg" in payload["files"]

    @pytest.mark.asyncio
    async def test_download_rejects_symlink_outside_output_dir(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        """Scenario: Symlinked files outside output_dir are excluded from download."""
        editor = await create_user("symlink@example.com", UserRole.EDITOR)
        output_dir = tmp_path / "carousel-output"
        output_dir.mkdir()
        outside = tmp_path / "outside-secret.txt"
        outside.write_text("secret", encoding="utf-8")
        (output_dir / "slide_1.jpg").write_bytes(b"jpeg")
        link = output_dir / "escape.txt"
        link.symlink_to(outside)

        from rag_backend.infrastructure.database.carousel_repository import (
            PostgresCarouselRepository,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = PostgresCarouselRepository(session)
            project = CarouselProject(
                topic="Symlink test",
                audience="Devs",
                niche="AI",
                theme=CarouselTheme.AI_COMPETITION,
                owner_id=str(editor.id),
                output_dir=str(output_dir),
            )
            created = await repo.create_project(project)
            await session.commit()
            project_id = str(created.id)

        response = await client.get(
            f"/api/carousels/{project_id}/download",
            headers=auth_header(editor),
        )
        assert response.status_code == 200
        files = response.json()["files"]
        assert "slide_1.jpg" in files
        assert "escape.txt" not in files
