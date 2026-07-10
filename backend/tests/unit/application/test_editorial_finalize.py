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

        # AE-0121: the artifact build/activation is invoked through the presentation
        # CarouselArtifactBuildAdapter (editorial → presentation). Patch that
        # adapter to return a successful ArtifactActivation; the activation CAS
        # itself is exercised by the adapter's own tests + the safety net.
        from rag_backend.modules.presentation import ArtifactActivation

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
                "rag_backend.application.services.carousel.editorial_finalize.CarouselArtifactBuildAdapter",
            ) as mock_build_adapter,
        ):
            mock_build_adapter.return_value.build_and_activate = AsyncMock(
                return_value=ArtifactActivation(
                    ok=True, artifact_version="sha256-" + "a" * 64
                )
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

    async def test_completed_project_render_failure_is_preserved(self) -> None:
        """AE-0313: a failed re-finalize/republish never mark_failed's completed."""
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            output_dir="/tmp/out",
            status=CarouselStatus.COMPLETED,
        )
        repo = AsyncMock()
        repo.get_project_by_id = AsyncMock(return_value=project)
        refinement = AsyncMock()
        refinement.re_render_slides = AsyncMock(side_effect=ValueError("no slides"))

        with patch(
            "rag_backend.application.services.carousel.editorial_finalize.PostgresCarouselRepository",
            return_value=repo,
        ):
            result = await export_and_complete_carousel(
                MagicMock(), refinement, str(project.id)
            )

        assert project.status == CarouselStatus.COMPLETED
        assert project.error_message is None
        repo.update_project.assert_not_called()
        assert not result.completed
        assert result.errors

    async def test_completed_project_health_failure_is_preserved(self) -> None:
        """AE-0313: a health-check failure on a completed project is returned,
        not persisted — the prior artifact version keeps serving."""
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            output_dir="/tmp/out",
            status=CarouselStatus.COMPLETED,
        )
        repo = AsyncMock()
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[])
        rendered = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            output_dir="/tmp/out",
            status=CarouselStatus.COMPLETED,
        )
        refinement = AsyncMock()
        refinement.re_render_slides = AsyncMock(return_value=rendered)

        with (
            patch(
                "rag_backend.application.services.carousel.editorial_finalize.PostgresCarouselRepository",
                return_value=repo,
            ),
            patch(
                "rag_backend.application.services.carousel.editorial_finalize.evaluate_carousel_artifacts",
                return_value=MagicMock(ok=False, errors=("pt PDF missing",)),
            ),
        ):
            result = await export_and_complete_carousel(
                MagicMock(), refinement, str(project.id)
            )

        assert rendered.status == CarouselStatus.COMPLETED
        assert rendered.error_message is None
        repo.update_project.assert_not_called()
        assert not result.completed
        assert "pt PDF missing" in result.errors


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
