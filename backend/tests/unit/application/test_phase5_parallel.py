"""Unit tests for parallel image generation (phase 5)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from rag_backend.application.services.carousel_agent import CarouselAgent, SlideData
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus


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


def _agent_with_image_service(image_service: AsyncMock) -> tuple[CarouselAgent, AsyncMock]:
    repo = AsyncMock()
    repo.update_project = AsyncMock(side_effect=lambda p: p)
    registry = ImageProviderRegistry(gemini_service=image_service, openai_service=image_service)
    agent = CarouselAgent(
        repository=repo,
        llm_service=AsyncMock(),
        research_tool=AsyncMock(),
        image_registry=registry,
        export_service=AsyncMock(),
        output_base_dir="/tmp",
    )
    return agent, repo


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
        agent, _ = _agent_with_image_service(image_service)

        slides = [_slide_data(i) for i in range(1, 5)]
        await agent._phase5_images(_project(tmp_path), slides, tmp_path)

        assert call_count == 4
        # 4 concurrent calls, not 1 at a time.
        assert max_concurrent == 4

    async def test_publishes_per_slide_status_lifecycle(self, tmp_path: Path) -> None:
        """Each slide transitions pending → in_flight → done on the project."""
        published_states: list[list[str]] = []

        async def capture(prompt: str, output_path: str) -> str:
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=capture)
        agent, repo = _agent_with_image_service(image_service)

        async def _track(project: CarouselProject) -> CarouselProject:
            if project.phase_progress and "slides" in project.phase_progress:
                slides = project.phase_progress["slides"]
                assert isinstance(slides, list)
                published_states.append([s["status"] for s in slides])
            return project

        repo.update_project = AsyncMock(side_effect=_track)

        slides = [_slide_data(i) for i in range(1, 3)]
        project = _project(tmp_path)
        await agent._phase5_images(project, slides, tmp_path)

        # First snapshot = all pending, last = all done.
        assert published_states[0] == ["pending", "pending"]
        assert published_states[-1] == ["done", "done"]
        assert any("in_flight" in state for state in published_states)

    async def test_failure_marks_slide_failed_and_propagates(self, tmp_path: Path) -> None:
        """One slide failing marks its slot 'failed' and raises."""
        captured_states: list[list[str]] = []

        async def flaky(prompt: str, output_path: str) -> str:
            if "slide 2" in prompt:
                raise RuntimeError("OpenAI flaked")
            return output_path

        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(side_effect=flaky)
        agent, repo = _agent_with_image_service(image_service)

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
            await agent._phase5_images(project, slides, tmp_path)

        # The failed slide's slot is marked "failed" before the exception bubbles.
        assert any("failed" in state for state in captured_states)

    async def test_slide_scene_snippet_populated(self, tmp_path: Path) -> None:
        """Each slide entry carries a short scene snippet for the UI."""
        image_service = AsyncMock()
        image_service.generate_image = AsyncMock(return_value="/tmp/x.jpg")
        agent, repo = _agent_with_image_service(image_service)

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
        await agent._phase5_images(project, slides, tmp_path)

        assert project.phase_progress is not None
        slide_entries = project.phase_progress.get("slides")
        assert isinstance(slide_entries, list)
        entry = slide_entries[0]
        assert entry["number"] == 1
        assert "neon cityscape" in str(entry["scene"])
