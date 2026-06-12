"""Unit tests for editorial finalize helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.editorial_finalize import (
    export_and_complete_carousel,
    finalize_carousel_after_images_approval,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus


@pytest.mark.asyncio
@pytest.mark.unit
class TestExportAndCompleteCarousel:
    async def test_skips_when_project_missing(self) -> None:
        repo = AsyncMock()
        repo.get_project_by_id = AsyncMock(return_value=None)

        with patch(
            "rag_backend.application.services.carousel.editorial_finalize.PostgresCarouselRepository",
            return_value=repo,
        ):
            await export_and_complete_carousel(MagicMock(), MagicMock(), str(uuid4()))

        repo.update_project.assert_not_called()

    async def test_skips_when_output_dir_missing(self) -> None:
        project = CarouselProject(topic="T", audience="A", niche="N")
        project.output_dir = None
        repo = AsyncMock()
        repo.get_project_by_id = AsyncMock(return_value=project)

        with patch(
            "rag_backend.application.services.carousel.editorial_finalize.PostgresCarouselRepository",
            return_value=repo,
        ):
            await export_and_complete_carousel(MagicMock(), MagicMock(), str(uuid4()))

        repo.update_project.assert_awaited_once()
        assert project.status == CarouselStatus.FAILED

    async def test_completes_after_render(self) -> None:
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            output_dir="/tmp/out",
            status=CarouselStatus.GENERATING_IMAGES,
        )
        repo = AsyncMock()
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[])
        refinement = AsyncMock()
        rendered = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            output_dir="/tmp/out",
        )
        refinement.re_render_slides = AsyncMock(return_value=rendered)

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_finalize.PostgresCarouselRepository",
                return_value=repo,
            ),
            patch(
                "rag_backend.application.services.carousel.design_token_utils.merge_design_tokens_with_disk",
                return_value={"primary": "#000"},
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_finalize.evaluate_carousel_artifacts",
                return_value=MagicMock(ok=True, errors=()),
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_finalize.read_project_lock_version",
                new=AsyncMock(return_value=2),
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_finalize.CarouselArtifactBuildService",
            ) as mock_build_service,
        ):
            build_result = MagicMock(
                artifact_version="sha256-" + "a" * 64,
                operation_id="op",
                lock_version=3,
                manifest_path=MagicMock(),
                version_dir=MagicMock(),
            )
            mock_build_service.return_value.build_and_activate = AsyncMock(
                return_value=build_result
            )
            await export_and_complete_carousel(MagicMock(), refinement, str(project.id))

        assert rendered.status == CarouselStatus.COMPLETED
        repo.update_project.assert_awaited_once_with(rendered)

    async def test_logs_warning_on_render_failure(self) -> None:
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            output_dir="/tmp/out",
        )
        repo = AsyncMock()
        repo.get_project_by_id = AsyncMock(return_value=project)
        refinement = AsyncMock()
        refinement.re_render_slides = AsyncMock(side_effect=ValueError("no slides"))

        with patch(
            "rag_backend.application.services.carousel.editorial_finalize.PostgresCarouselRepository",
            return_value=repo,
        ):
            await export_and_complete_carousel(MagicMock(), refinement, str(project.id))

        repo.update_project.assert_awaited_once()
        assert project.status == CarouselStatus.FAILED


@pytest.mark.asyncio
@pytest.mark.unit
class TestFinalizeCarouselAfterImagesApproval:
    async def test_builds_refinement_from_container(self) -> None:
        """Local imports make this hard to mock; we verify the happy path runs."""
        with (
            patch(
                "rag_backend.infrastructure.container.get_container"
            ) as mock_container,
            patch(
                "rag_backend.application.services.carousel.editorial_finalize.export_and_complete_carousel",
                new=AsyncMock(),
            ) as mock_export,
        ):
            container = MagicMock()
            container.llm_service = MagicMock(return_value=MagicMock())
            container.image_provider_registry = MagicMock(return_value=MagicMock())
            container.export_service = MagicMock(return_value=MagicMock())
            container.pdf_slide_builder = MagicMock(return_value=MagicMock())
            mock_container.return_value = container

            db = MagicMock()
            await finalize_carousel_after_images_approval(db, str(uuid4()))

        mock_export.assert_awaited_once()
