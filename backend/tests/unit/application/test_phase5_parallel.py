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
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from uuid import UUID

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
        """One slide failing marks its slot 'failed' and surfaces an error.

        AE-0209: the batch no longer cancels siblings — the failure is reported
        as an aggregate after the rest of the batch runs, with the original
        provider error chained as the cause.
        """
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

        with pytest.raises(RuntimeError) as exc_info:
            await run_images(
                ImageGenerationConfig(
                    project=project,
                    slides=slides,
                    output_dir=tmp_path,
                    repo=repo,
                    image_registry=registry,
                )
            )

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "flaked" in str(exc_info.value.__cause__)
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


class _FakeResponse:
    """Minimal stand-in for an httpx.Response carrying a retry-after header."""

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers
        self.status_code = 429


class _FakeRateLimitError(Exception):
    """Provider-shaped 429 with a retry-after header (no live SDK needed)."""

    def __init__(self, retry_after: str) -> None:
        super().__init__("Rate limit reached for gpt-image")
        self.status_code = 429
        self.response = _FakeResponse({"retry-after": retry_after})


@pytest.mark.unit
class TestRateLimitAwareGeneration:
    """AE-0208: a provider 429 is survived by honoring retry-after."""

    async def test_429_then_success_completes_phase(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Scenario: Given a provider that 429s once then succeeds, when the
        # images phase runs, then the runner waits >= the stated retry-after
        # and the phase completes instead of aborting.
        attempts = 0

        async def flaky(prompt: str, output_path: str) -> str:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise _FakeRateLimitError("12")
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=flaky)
        registry, repo = _registry_with_image_service(image_service)

        slept: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            slept.append(seconds)

        from rag_backend.application.services.carousel import image_rate_limit

        monkeypatch.setattr(image_rate_limit.asyncio, "sleep", fake_sleep)

        slides = [_slide_data(1)]
        project = _project(tmp_path)
        await run_images(
            ImageGenerationConfig(
                project=project,
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
                max_attempts=3,
            )
        )

        assert attempts == 2  # one 429, one success
        assert slept  # the runner waited
        assert slept[0] >= 12.0  # honored the stated retry-after

    async def test_concurrency_capped_to_config(self, tmp_path: Path) -> None:
        # Scenario: Given a concurrency cap of 2, when many slides generate,
        # then no more than 2 provider calls are ever in flight at once.
        max_concurrent = 0
        in_flight = 0
        lock = asyncio.Lock()

        async def slow(prompt: str, output_path: str) -> str:
            nonlocal max_concurrent, in_flight
            async with lock:
                in_flight += 1
                max_concurrent = max(max_concurrent, in_flight)
            await asyncio.sleep(0.02)
            async with lock:
                in_flight -= 1
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=slow)
        registry, repo = _registry_with_image_service(image_service)

        slides = [_slide_data(i) for i in range(1, 6)]
        await run_images(
            ImageGenerationConfig(
                project=_project(tmp_path),
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
                concurrency=2,
            )
        )

        assert max_concurrent <= 2


@pytest.mark.unit
class TestPartialCommitAndReentry:
    """AE-0209: a single-slide failure persists siblings; re-run completes."""

    @staticmethod
    def _slide_entity(project_id: UUID, n: int) -> CarouselSlide:
        return CarouselSlide(
            project_id=project_id,
            slide_number=n,
            slide_type="content" if n > 1 else "intro",
            heading=f"H{n}",
            body=f"B{n}",
            image_prompt=f"Scene for slide {n}",
        )

    async def test_sibling_persists_on_single_slide_failure(
        self, tmp_path: Path
    ) -> None:
        # Scenario: Given slide 2 fails, when the batch runs, then slide 1's
        # image_path is still written back to its slide row (partial commit)
        # and an aggregate error is surfaced.
        project = _project(tmp_path)
        entities = [self._slide_entity(project.id, i) for i in range(1, 3)]

        async def flaky(prompt: str, output_path: str) -> str:
            if "slide 2" in prompt:
                raise RuntimeError("OpenAI flaked")
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=flaky)
        registry, repo = _registry_with_image_service(image_service)
        repo.get_slides_by_project = AsyncMock(return_value=entities)

        updated_slides: list[CarouselSlide] = []

        async def _capture_slide(slide: CarouselSlide) -> CarouselSlide:
            updated_slides.append(slide)
            return slide

        repo.update_slide = AsyncMock(side_effect=_capture_slide)

        slides = [_slide_data(i) for i in range(1, 3)]
        with pytest.raises(RuntimeError):
            await run_images(
                ImageGenerationConfig(
                    project=project,
                    slides=slides,
                    output_dir=tmp_path,
                    repo=repo,
                    image_registry=registry,
                )
            )

        committed = {s.slide_number for s in updated_slides}
        assert 1 in committed  # the good slide was persisted despite slide 2 failing

    async def test_rerun_regenerates_only_missing_and_completes(
        self, tmp_path: Path
    ) -> None:
        # Scenario: Given slide 1 already has an image on disk + a matching
        # generation key, when the phase re-runs, then slide 1 is reused (not
        # regenerated) and the phase completes.
        project = _project(tmp_path)
        slide1 = self._slide_entity(project.id, 1)
        slide2 = self._slide_entity(project.id, 2)

        # Pre-seed slide 1 as already generated: a real JPEG on disk + the
        # generation key that the prompt package will resolve to.
        from rag_backend.application.services.carousel.image_prompt_package import (
            METADATA_GENERATION_KEY,
            ImagePromptPackageRequest,
            render_image_prompt_package,
        )
        from rag_backend.application.services.carousel.theme_resolver import (
            resolve_theme,
        )

        images_dir = tmp_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        existing = images_dir / "slide_1.jpg"
        from PIL import Image as PILImage

        PILImage.new("RGB", (4, 4)).save(existing, "JPEG")
        prompt1 = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=project,
                slide=_slide_data(1),
                theme=resolve_theme(project),
            )
        )
        slide1.image_path = str(existing)
        slide1.metadata = {METADATA_GENERATION_KEY: prompt1.generation_key}

        generated_for: list[str] = []

        async def generate(prompt: str, output_path: str) -> str:
            generated_for.append(output_path)
            from PIL import Image as Inner

            Inner.new("RGB", (4, 4)).save(output_path, "JPEG")
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=generate)
        registry, repo = _registry_with_image_service(image_service)
        repo.get_slides_by_project = AsyncMock(return_value=[slide1, slide2])
        # The record-lookup reuse path returns no usable record (AsyncMock is
        # not a CarouselImageGeneration), so reuse falls to the on-disk legacy
        # path keyed by generation_key — exactly the re-entry path under test.

        slides = [_slide_data(1), _slide_data(2)]
        await run_images(
            ImageGenerationConfig(
                project=project,
                slides=slides,
                output_dir=tmp_path,
                repo=repo,
                image_registry=registry,
            )
        )

        # Only the missing slide (2) was generated; slide 1 was reused.
        assert all("slide_1.jpg" not in path for path in generated_for)
        assert any("slide_2.jpg" in path for path in generated_for)


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
