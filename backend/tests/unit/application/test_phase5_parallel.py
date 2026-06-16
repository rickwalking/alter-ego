"""Unit tests for parallel image generation (phase 5)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from rag_backend.application.services.carousel.nodes.images import (
    ImageGenerationConfig,
    run_images,
)
from rag_backend.application.services.carousel.types import SlideData
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from rag_backend.modules.presentation import ProgressSnapshot


def _project(tmp_path: Path) -> CarouselProject:
    return CarouselProject(
        topic="T",
        audience="A",
        niche="N",
        status=CarouselStatus.GENERATING_IMAGES,
        output_dir=str(tmp_path),
    )


def _slide_data(n: int) -> SlideData:
    return SlideData(
        slide_number=n,
        slide_type="content" if n > 1 else "intro",
        heading=f"H{n}",
        body=f"B{n}",
        image_prompt=f"Scene for slide {n}",
    )


def _statuses(snapshot: ProgressSnapshot) -> list[str]:
    """Extract per-slide status strings from a reported progress snapshot."""
    return [str(slide["status"]) for slide in snapshot.slides]


class _CallbackPort:
    """Adapts an async reporter callable to the WorkflowProgressPort protocol."""

    def __init__(self, reporter: Callable[[ProgressSnapshot], Awaitable[None]]) -> None:
        self._reporter = reporter

    async def report_progress(self, snapshot: ProgressSnapshot) -> None:
        await self._reporter(snapshot)


def _registry_with_image_service(
    image_service: AsyncMock,
) -> tuple[ImageProviderRegistry, AsyncMock]:
    repo = AsyncMock()
    repo.update_project = AsyncMock(side_effect=lambda p: p)
    repo.get_slides_by_project = AsyncMock(return_value=[])
    repo.update_slide = AsyncMock(side_effect=lambda slide: slide)
    registry = ImageProviderRegistry(
        gemini_service=image_service, openai_service=image_service
    )
    return registry, repo


@pytest.mark.unit
class TestParallelImageGeneration:
    """Phase 5 runs all slide-image requests concurrently."""

    async def test_all_slides_run_concurrently(self, tmp_path: Path) -> None:
        """Total wall time <= max(single request), not sum of all."""
        call_count = 0
        max_concurrent = 0
        in_flight = 0
        lock = asyncio.Lock()

        async def slow_generate(prompt: str, output_path: str) -> str:
            nonlocal call_count, max_concurrent, in_flight
            async with lock:
                in_flight += 1
                max_concurrent = max(max_concurrent, in_flight)
                call_count += 1
            await asyncio.sleep(0.1)
            async with lock:
                in_flight -= 1
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=slow_generate)
        registry, repo = _registry_with_image_service(image_service)

        slides = [_slide_data(i) for i in range(1, 5)]
        await run_images(
            ImageGenerationConfig(
                project=_project(tmp_path),
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
            )
        )

        assert call_count == 4
        assert max_concurrent == 4

    async def test_publishes_per_slide_status_lifecycle(self, tmp_path: Path) -> None:
        """Each slide transitions pending → in_flight → done on the project."""
        published_states: list[list[str]] = []

        async def capture(prompt: str, output_path: str) -> str:
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=capture)
        registry, repo = _registry_with_image_service(image_service)

        async def _track(project: CarouselProject) -> CarouselProject:
            if project.phase_progress and "slides" in project.phase_progress:
                slides = project.phase_progress["slides"]
                assert isinstance(slides, list)
                published_states.append([s["status"] for s in slides])
            return project

        repo.update_project = AsyncMock(side_effect=_track)

        slides = [_slide_data(i) for i in range(1, 3)]
        project = _project(tmp_path)
        await run_images(
            ImageGenerationConfig(
                project=project,
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
            )
        )

        assert published_states[0] == ["pending", "pending"]
        assert published_states[-1] == ["done", "done"]
        assert any("in_flight" in state for state in published_states)

    async def test_persists_image_path_on_slide_rows(self, tmp_path: Path) -> None:
        """Successful generation writes image_path back to slide rows."""
        from uuid import uuid4

        from rag_backend.domain.models import CarouselSlide

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(
            side_effect=lambda prompt, output_path: output_path
        )
        registry, repo = _registry_with_image_service(image_service)
        slide_entity = CarouselSlide(
            id=uuid4(),
            project_id=_project(tmp_path).id,
            slide_number=1,
            slide_type="intro",
            heading="H1",
            body="B1",
            image_prompt="Scene",
        )
        repo.get_slides_by_project = AsyncMock(return_value=[slide_entity])

        slides = [_slide_data(1)]
        await run_images(
            ImageGenerationConfig(
                project=_project(tmp_path),
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
            )
        )

        repo.update_slide.assert_awaited()
        updated = repo.update_slide.await_args.args[0]
        assert updated.image_path.endswith("slide_1.jpg")

    async def test_failure_marks_slide_failed_and_propagates(
        self, tmp_path: Path
    ) -> None:
        """One slide failing marks its slot 'failed' and raises."""
        captured_states: list[list[str]] = []

        async def flaky(prompt: str, output_path: str) -> str:
            if "slide 2" in prompt:
                raise RuntimeError("OpenAI flaked")
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=flaky)
        registry, repo = _registry_with_image_service(image_service)

        async def _track(project: CarouselProject) -> CarouselProject:
            if project.phase_progress and "slides" in project.phase_progress:
                slides = project.phase_progress["slides"]
                assert isinstance(slides, list)
                captured_states.append([s["status"] for s in slides])
            return project

        repo.update_project = AsyncMock(side_effect=_track)

        slides = [_slide_data(i) for i in range(1, 3)]
        project = _project(tmp_path)

        with pytest.raises(RuntimeError, match="flaked"):
            await run_images(
                ImageGenerationConfig(
                    project=project,
                    slides=slides,
                    output_dir=tmp_path,
                    repo=repo,
                    image_registry=registry,
                )
            )

        assert any("failed" in state for state in captured_states)

    async def test_slide_scene_snippet_populated(self, tmp_path: Path) -> None:
        """Each slide entry carries a short scene snippet for the UI."""
        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(return_value="/tmp/x.jpg")
        registry, repo = _registry_with_image_service(image_service)

        slides = [
            SlideData(
                slide_number=1,
                slide_type="intro",
                heading="H",
                body="B",
                image_prompt="A stunning neon cityscape with floating holographic displays",
            ),
        ]
        project = _project(tmp_path)
        await run_images(
            ImageGenerationConfig(
                project=project,
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
            )
        )

        assert project.phase_progress is not None
        slide_entries = project.phase_progress.get("slides")
        assert isinstance(slide_entries, list)
        entry = slide_entries[0]
        assert entry["number"] == 1
        assert "neon cityscape" in str(entry["scene"])


@pytest.mark.unit
class TestProgressCallbackPort:
    """AE-0121: the image node reports progress via the presentation→editorial
    callback port when injected (editorial owns the phase_progress write)."""

    async def test_callback_receives_snapshots_and_repo_progress_write_skipped(
        self, tmp_path: Path
    ) -> None:
        """With a progress port, progress goes through the callback, not the repo.

        The node must NOT write ``phase_progress`` via ``repo.update_project`` when
        editorial owns it — and the reported snapshots reproduce the legacy
        ``phase_progress`` payload exactly (same status lifecycle).
        """
        received: list[ProgressSnapshot] = []

        async def reporter(snapshot: ProgressSnapshot) -> None:
            received.append(snapshot)

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(
            side_effect=lambda prompt, output_path: output_path
        )
        registry, repo = _registry_with_image_service(image_service)

        slides = [_slide_data(i) for i in range(1, 3)]
        project = _project(tmp_path)
        await run_images(
            ImageGenerationConfig(
                project=project,
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
                progress_port=_CallbackPort(reporter),
            )
        )

        # The repo NEVER persisted progress (presentation does not write state).
        repo.update_project.assert_not_called()
        # The callback received the lifecycle snapshots (pending → … → done).
        assert received
        assert _statuses(received[0]) == ["pending", "pending"]
        assert _statuses(received[-1]) == ["done", "done"]
        # The dict phase value is the legacy generating_images value.
        assert received[0].phase == "generating_images"
        assert received[0].sse_phase == "images"

    async def test_no_callback_preserves_legacy_in_node_write(
        self, tmp_path: Path
    ) -> None:
        """Without a progress port, the node still writes phase_progress (legacy)."""
        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(
            side_effect=lambda prompt, output_path: output_path
        )
        registry, repo = _registry_with_image_service(image_service)

        slides = [_slide_data(1)]
        project = _project(tmp_path)
        await run_images(
            ImageGenerationConfig(
                project=project,
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
            )
        )

        repo.update_project.assert_awaited()
        assert project.phase_progress is not None
        assert project.phase_progress["phase"] == "generating_images"
