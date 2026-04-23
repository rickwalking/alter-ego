"""Unit tests for CarouselAgent.re_render_slides + unpack_extras helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.types import (
    SlideData,
    pack_extras,
    unpack_extras,
)
from rag_backend.application.services.carousel_agent import CarouselAgent
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
)


def _slide(number: int, extras: dict[str, object] | None = None) -> CarouselSlide:
    return CarouselSlide(
        project_id=uuid4(),
        slide_number=number,
        slide_type="content",
        heading=f"Heading {number}",
        body=f"Body {number}",
        image_prompt="A scene",
        extras=extras,
    )


@pytest.mark.unit
class TestExtrasRoundTrip:
    """Pack and unpack should preserve the structured render cards."""

    def test_pack_includes_features_stats_insight(self) -> None:
        sd = SlideData(
            slide_number=2,
            slide_type="content",
            heading="H",
            body="B",
            image_prompt="scene",
            features=[{"icon": "🧠", "title": "T", "body": "B"}],
            stats=[{"value": "80%", "label": "L", "detail": ""}],
            insight={"quote": "Q", "attribution": "A"},
        )
        packed = pack_extras(sd)
        assert packed is not None
        assert packed["features"] == sd.features
        assert packed["stats"] == sd.stats
        assert packed["insight"] == sd.insight
        assert packed["image_prompt"] == "scene"

    def test_pack_returns_none_when_empty(self) -> None:
        sd = SlideData(slide_number=1, slide_type="intro", heading="H", body="B")
        assert pack_extras(sd) is None

    def test_unpack_restores_features_from_db_slide(self) -> None:
        slide = _slide(
            3,
            extras={
                "features": [{"icon": "📝", "title": "T", "body": "B"}],
                "stats": None,
                "insight": None,
                "image_prompt": "scene from extras",
            },
        )
        slide.image_prompt = None  # ensure unpack falls back to extras
        sd = unpack_extras(slide)
        assert sd.features == [{"icon": "📝", "title": "T", "body": "B"}]
        assert sd.image_prompt == "scene from extras"
        assert sd.heading == "Heading 3"


def _agent_with_mocks() -> tuple[CarouselAgent, AsyncMock, AsyncMock, MagicMock]:
    repo = AsyncMock()
    repo.update_project = AsyncMock(side_effect=lambda p: p)
    repo.get_slides_by_project = AsyncMock()
    export = AsyncMock()
    export.export_slides = AsyncMock(return_value=["/tmp/slide_1.jpg", "/tmp/slide_2.jpg"])
    pdf_builder = MagicMock()
    pdf_builder.build = MagicMock(return_value="/tmp/carousel.pdf")
    image_service = AsyncMock()
    registry = ImageProviderRegistry(gemini_service=image_service, openai_service=image_service)
    agent = CarouselAgent(
        repository=repo,
        llm_service=AsyncMock(),
        research_tool=AsyncMock(),
        image_registry=registry,
        export_service=export,
        pdf_slide_builder=pdf_builder,
        output_base_dir="/tmp",
    )
    return agent, repo, export, pdf_builder


@pytest.mark.unit
class TestReRenderSlides:
    """The refine flow's re-render entry point."""

    async def test_re_render_writes_pdf_and_bumps_updated_at(self, tmp_path: Path) -> None:
        agent, repo, export, pdf_builder = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slides = [_slide(1), _slide(2)]
        repo.get_slides_by_project = AsyncMock(return_value=slides)
        original_updated_at = project.updated_at

        result = await agent.re_render_slides(project.id)

        export.export_slides.assert_awaited_once()
        pdf_builder.build.assert_called_once()
        assert result.pdf_path == "/tmp/carousel.pdf"
        assert result.updated_at != original_updated_at
        repo.update_project.assert_awaited()

    async def test_re_render_raises_when_project_missing(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        repo.get_project_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await agent.re_render_slides(uuid4())

    async def test_re_render_raises_when_no_output_dir(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=None,
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        with pytest.raises(ValueError, match="output_dir"):
            await agent.re_render_slides(project.id)

    async def test_re_render_raises_when_no_slides(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/x",
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[])
        with pytest.raises(ValueError, match="no slides"):
            await agent.re_render_slides(project.id)


@pytest.mark.unit
class TestRegenerateSlideImage:
    """The image regeneration flow."""

    async def test_regenerate_image_rewrites_prompt_and_exports(self, tmp_path: Path) -> None:
        agent, repo, export, pdf_builder = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slide = _slide(2, extras={"image_prompt": "old scene"})
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1), slide])
        agent._llm.generate = AsyncMock(return_value="new futuristic scene")

        result = await agent.regenerate_slide_image(project.id, 2, "make it futuristic")

        assert slide.image_prompt == "new futuristic scene"
        assert slide.extras is not None
        assert slide.extras.get("image_prompt") == "new futuristic scene"
        repo.update_slide.assert_awaited()
        export.export_slides.assert_awaited_once()
        pdf_builder.build.assert_called_once()
        assert result.id == project.id

    async def test_regenerate_raises_when_project_missing(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        repo.get_project_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await agent.regenerate_slide_image(uuid4(), 1, "change colors")

    async def test_regenerate_raises_when_no_output_dir(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=None,
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        with pytest.raises(ValueError, match="output_dir"):
            await agent.regenerate_slide_image(project.id, 1, "change colors")

    async def test_regenerate_raises_when_slide_missing(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/x",
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        repo.get_slides_by_project = AsyncMock(return_value=[_slide(1)])
        with pytest.raises(ValueError, match="Slide 2 not found"):
            await agent.regenerate_slide_image(project.id, 2, "change colors")

    async def test_regenerate_raises_when_no_image_prompt(self) -> None:
        agent, repo, _, _ = _agent_with_mocks()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir="/tmp/x",
        )
        repo.get_project_by_id = AsyncMock(return_value=project)
        slide = _slide(1)
        slide.image_prompt = None
        slide.extras = None
        repo.get_slides_by_project = AsyncMock(return_value=[slide])
        with pytest.raises(ValueError, match="no image_prompt"):
            await agent.regenerate_slide_image(project.id, 1, "change colors")
