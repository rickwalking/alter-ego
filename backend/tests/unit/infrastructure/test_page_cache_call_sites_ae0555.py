"""The slide export and the artifact activation release the files they wrote.

Feature: tests/features/worker_page_cache_ae0555.feature
"""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.artifact_build_types import (
    ArtifactBuildFailure,
    ArtifactBuildResult,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.domain.protocols import ExportConfig
from rag_backend.infrastructure.external.playwright_export import (
    PlaywrightExportService,
)
from rag_backend.modules.presentation.infrastructure.editorial_workflow_ports import (
    CarouselArtifactBuildAdapter,
)

_EXPORT = "rag_backend.infrastructure.external.playwright_export"
_PORTS = "rag_backend.modules.presentation.infrastructure.editorial_workflow_ports"
_BUILD = "rag_backend.application.services.carousel.artifact_build_service"
_VERSION = "sha256-built"


@pytest.mark.unit
class TestExportReleasesItsSlides:
    async def test_export_releases_the_output_directory_after_rendering(
        self, tmp_path: Path
    ) -> None:
        """Scenario: A slide export releases the slides it wrote."""
        order: list[str] = []
        slide = str(tmp_path / "slide_1.jpg")

        async def render(html_file: Path, cfg: ExportConfig) -> list[str]:
            del html_file, cfg
            order.append("render")
            return [slide]

        def release(root: Path) -> int:
            order.append(f"release:{root}")
            return 1

        with (
            patch(f"{_EXPORT}._render_slides", side_effect=render),
            patch(f"{_EXPORT}.release_page_cache", side_effect=release),
        ):
            result = await PlaywrightExportService.export_slides(
                html_content="<html></html>", output_dir=str(tmp_path)
            )

        assert result == [slide]
        assert order == ["render", f"release:{tmp_path}"]

    async def test_a_failed_render_releases_nothing(self, tmp_path: Path) -> None:
        release = MagicMock(return_value=0)
        with (
            patch(
                f"{_EXPORT}._render_slides",
                new_callable=AsyncMock,
                side_effect=RuntimeError("chromium crashed"),
            ),
            patch(f"{_EXPORT}.release_page_cache", release),
            pytest.raises(RuntimeError),
        ):
            await PlaywrightExportService.export_slides(
                html_content="<html></html>", output_dir=str(tmp_path)
            )

        release.assert_not_called()


class _Repo:
    def __init__(self, project: CarouselProject) -> None:
        self._project = project

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        del project_id
        return self._project

    async def get_slides_by_project(self, project_id: UUID) -> list[CarouselSlide]:
        del project_id
        return []


def _project(output_dir: str | None) -> CarouselProject:
    return CarouselProject(topic="t", audience="a", niche="n", output_dir=output_dir)


async def _activate(
    project: CarouselProject, outcome: ArtifactBuildResult | ArtifactBuildFailure
) -> MagicMock:
    release = MagicMock(return_value=3)
    adapter = CarouselArtifactBuildAdapter(
        db=cast("AsyncSession", object()), repository=_Repo(project)
    )
    with (
        patch(f"{_BUILD}.read_project_lock_version", AsyncMock(return_value=2)),
        patch(
            f"{_BUILD}.CarouselArtifactBuildService.build_and_activate",
            AsyncMock(return_value=outcome),
        ),
        patch(f"{_PORTS}.release_page_cache", release),
    ):
        activation = await adapter.build_and_activate(str(project.id))
    assert activation.ok is isinstance(outcome, ArtifactBuildResult)
    return release


def _built(tmp_path: Path) -> ArtifactBuildResult:
    return ArtifactBuildResult(
        artifact_version=_VERSION,
        operation_id="op",
        lock_version=3,
        manifest_path=tmp_path / "manifest.json",
        version_dir=tmp_path,
    )


@pytest.mark.unit
class TestActivationReleasesTheOutputTree:
    async def test_activation_releases_the_project_output_directory(
        self, tmp_path: Path
    ) -> None:
        """Scenario: A promoted artifact releases the whole carousel output."""
        release = await _activate(_project(str(tmp_path)), _built(tmp_path))

        release.assert_called_once_with(tmp_path)

    async def test_a_failed_activation_releases_nothing(self, tmp_path: Path) -> None:
        failure = ArtifactBuildFailure(artifact_version=_VERSION, errors=("conflict",))

        release = await _activate(_project(str(tmp_path)), failure)

        release.assert_not_called()

    async def test_a_project_without_output_dir_releases_nothing(
        self, tmp_path: Path
    ) -> None:
        release = await _activate(_project(None), _built(tmp_path))

        release.assert_not_called()
