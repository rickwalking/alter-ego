"""Unit tests for bilingual slide export and EN translation handling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.refinement_service import (
    BilingualExportParams,
    CarouselRefinementConfig,
    CarouselRefinementService,
)
from rag_backend.application.services.carousel.types import (
    SlideData,
    build_slides_en_index,
    slides_data_for_language,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
)


@pytest.mark.unit
class TestBuildSlidesEnIndex:
    """Bilingual slides_en parsing."""

    def test_indexes_by_slide_number(self) -> None:
        idx = build_slides_en_index([
            {"number": 1, "heading": "EN H1", "body": "EN B1"},
            {"number": 2, "heading": "EN H2", "body": "EN B2"},
        ])
        assert set(idx.keys()) == {1, 2}
        assert idx[1]["heading"] == "EN H1"

    def test_tolerates_missing_field(self) -> None:
        assert build_slides_en_index(None) == {}
        assert build_slides_en_index("nonsense") == {}

    def test_skips_items_without_number(self) -> None:
        idx = build_slides_en_index([{"heading": "no number"}])
        assert idx == {}


@pytest.mark.unit
class TestSlidesDataForLanguage:
    """Per-language SlideData materialization."""

    def test_pt_returns_originals_unchanged(self) -> None:
        slides = [SlideData(1, "intro", "PT", "PT body")]
        assert slides_data_for_language(slides, "pt") is slides

    def test_en_swaps_text_when_translation_present(self) -> None:
        slide = SlideData(
            1,
            "intro",
            "PT heading",
            "PT body",
            translation_en={"heading": "EN heading", "body": "EN body"},
        )
        en_slides = slides_data_for_language([slide], "en")
        assert en_slides[0].heading == "EN heading"
        assert en_slides[0].body == "EN body"

    def test_en_falls_back_to_pt_when_no_translation(self) -> None:
        slide = SlideData(1, "intro", "PT", "PT body")
        en_slides = slides_data_for_language([slide], "en")
        assert en_slides[0].heading == "PT"

    # AE-0211 regression: a lowercase EN render-source (translation_en) heading
    # and body must be sentence-cased before the renderer consumes them. The
    # localized_slides repair path was bypassed in prod (project b5b61790), so
    # the render source itself must guarantee sentence case.
    def test_en_render_source_lowercase_heading_is_sentence_cased(self) -> None:
        slide = SlideData(
            1,
            "intro",
            "PT heading",
            "PT body",
            translation_en={
                "heading": "all lowercase en heading",
                "body": "all lowercase en body",
            },
        )
        en_slides = slides_data_for_language([slide], "en")
        assert en_slides[0].heading == "All lowercase en heading"
        assert en_slides[0].body == "All lowercase en body"

    def test_en_render_source_skips_leading_html_tag_when_casing(self) -> None:
        slide = SlideData(
            1,
            "intro",
            "PT heading",
            "PT body",
            translation_en={
                "heading": "<b>insight</b> for builders",
                "body": "<span>plain</span> body",
            },
        )
        en_slides = slides_data_for_language([slide], "en")
        assert en_slides[0].heading == "<b>Insight</b> for builders"
        assert en_slides[0].body == "<span>Plain</span> body"

    def test_en_render_source_preserves_already_sentence_cased(self) -> None:
        slide = SlideData(
            1,
            "intro",
            "PT heading",
            "PT body",
            translation_en={"heading": "Already cased", "body": "Already cased body"},
        )
        en_slides = slides_data_for_language([slide], "en")
        assert en_slides[0].heading == "Already cased"
        assert en_slides[0].body == "Already cased body"


def _agent_with_export_mock(
    tmp_path: Path,
) -> tuple[CarouselRefinementService, AsyncMock, MagicMock]:
    repo = AsyncMock()
    repo.update_project = AsyncMock(side_effect=lambda p: p)
    repo.get_slides_by_project = AsyncMock()
    export = AsyncMock()
    export.export_slides = AsyncMock(
        side_effect=[
            # PT standard
            [
                str(tmp_path / "pt" / "slide_1.jpg"),
                str(tmp_path / "pt" / "slide_2.jpg"),
            ],
            # PT HD
            [
                str(tmp_path / "pt" / "hd" / "slide_1.jpg"),
                str(tmp_path / "pt" / "hd" / "slide_2.jpg"),
            ],
            # EN standard
            [
                str(tmp_path / "en" / "slide_1.jpg"),
                str(tmp_path / "en" / "slide_2.jpg"),
            ],
            # EN HD
            [
                str(tmp_path / "en" / "hd" / "slide_1.jpg"),
                str(tmp_path / "en" / "hd" / "slide_2.jpg"),
            ],
        ]
    )
    pdf_builder = MagicMock()
    pdf_builder.build = MagicMock(
        side_effect=[
            str(tmp_path / "pt" / "carousel.pdf"),
            str(tmp_path / "en" / "carousel.pdf"),
        ]
    )
    image_service = AsyncMock()
    registry = ImageProviderRegistry(
        gemini_service=image_service, openai_service=image_service
    )
    agent = CarouselRefinementService(
        CarouselRefinementConfig(
            repository=repo,
            llm_service=AsyncMock(),
            image_registry=registry,
            export_service=export,
            pdf_slide_builder=pdf_builder,
        )
    )
    return agent, export, pdf_builder


@pytest.mark.unit
class TestBilingualExport:
    """Phase 6 fans out PT + EN renders when translations exist."""

    async def test_renders_both_languages_when_en_present(self, tmp_path: Path) -> None:
        agent, export, pdf_builder = _agent_with_export_mock(tmp_path)
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        slides = [
            SlideData(
                1,
                "intro",
                "PT H1",
                "PT B1",
                translation_en={"heading": "EN H1", "body": "EN B1"},
            ),
            SlideData(
                2,
                "content",
                "PT H2",
                "PT B2",
                translation_en={"heading": "EN H2", "body": "EN B2"},
            ),
        ]
        await agent._phase6_bilingual_export(
            BilingualExportParams(
                project=project,
                slides_data=slides,
                pt_html="<html>pt</html>",
                output_dir=tmp_path,
                strategy_name=None,
            )
        )

        # Each language calls export_slides twice (standard + HD)
        assert export.export_slides.await_count == 4
        assert export.export_slides.call_args_list[1].kwargs["config"].hd is True
        assert export.export_slides.call_args_list[3].kwargs["config"].hd is True
        assert pdf_builder.build.call_count == 2
        assert project.pdf_path is not None
        assert project.pdf_path_en is not None
        assert "/pt/" in project.pdf_path
        assert "/en/" in project.pdf_path_en

    async def test_skips_en_when_no_translations(self, tmp_path: Path) -> None:
        agent, export, pdf_builder = _agent_with_export_mock(tmp_path)
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        slides = [SlideData(1, "intro", "PT", "PT body")]
        await agent._phase6_bilingual_export(
            BilingualExportParams(
                project=project,
                slides_data=slides,
                pt_html="<html>pt</html>",
                output_dir=tmp_path,
                strategy_name=None,
            )
        )

        # PT-only: standard + HD = 2 calls
        assert export.export_slides.await_count == 2
        assert pdf_builder.build.call_count == 1
        assert project.pdf_path_en is None

    async def test_render_language_rewrites_image_paths(self, tmp_path: Path) -> None:
        from rag_backend.application.services.carousel.nodes.export import (
            BilingualExportConfig,
            render_language,
        )

        agent, export, pdf_builder = _agent_with_export_mock(tmp_path)
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            status=CarouselStatus.COMPLETED,
            output_dir=str(tmp_path),
        )
        config = BilingualExportConfig(
            project=project,
            slides_data=[],
            pt_html="",
            output_dir=tmp_path,
            export=export,
            pdf_builder=pdf_builder,
            language="pt",
            html_content=(
                '<img src="images/slide_1.jpg">'
                "<style>.bg{background:url('images/slide_1.jpg')}</style>"
            ),
        )
        await render_language(config)
        # Standard export uses ../images/
        standard_html = export.export_slides.await_args_list[0].kwargs["html_content"]
        assert "../images/slide_1.jpg" in standard_html
        assert 'src="images/slide_1' not in standard_html
        assert "url('../images/slide_1.jpg')" in standard_html
        assert "url('images/slide_1" not in standard_html

        # HD export uses ../../images/
        hd_html = export.export_slides.await_args_list[1].kwargs["html_content"]
        assert "../../images/slide_1.jpg" in hd_html
        assert 'src="images/slide_1' not in hd_html
        assert "url('../../images/slide_1.jpg')" in hd_html
        assert "url('images/slide_1" not in hd_html


def _slide(number: int, extras: dict[str, object] | None = None) -> CarouselSlide:
    return CarouselSlide(
        project_id=uuid4(),
        slide_number=number,
        slide_type="content",
        heading=f"PT heading {number}",
        body=f"PT body {number}",
        extras=extras,
    )


@pytest.mark.unit
class TestRefineSlideEnLanguage:
    """slide_*:N:en selectors mutate translation_en in extras."""

    async def test_resolve_slide_heading_en_uses_translation(self) -> None:
        from rag_backend.application.tools.carousel.refine_copy import (
            _resolve_refine_target,
        )

        repo = AsyncMock()
        repo.update_slide = AsyncMock()
        slide = _slide(
            2,
            extras={"translation_en": {"heading": "EN heading", "body": "EN body"}},
        )
        repo.get_slides_by_project = AsyncMock(return_value=[slide])

        project = CarouselProject(topic="T", audience="A", niche="N")
        original, setter = await _resolve_refine_target(
            project, "slide_heading:2:en", repo
        )
        assert original == "EN heading"

        await setter("Reworked EN heading")
        assert slide.extras is not None
        assert isinstance(slide.extras, dict)
        translation = slide.extras.get("translation_en")
        assert isinstance(translation, dict)
        assert translation.get("heading") == "Reworked EN heading"

    async def test_resolve_slide_body_pt_default(self) -> None:
        from rag_backend.application.tools.carousel.refine_copy import (
            _resolve_refine_target,
        )

        repo = AsyncMock()
        repo.update_slide = AsyncMock()
        slide = _slide(3)
        repo.get_slides_by_project = AsyncMock(return_value=[slide])

        project = CarouselProject(topic="T", audience="A", niche="N")
        original, setter = await _resolve_refine_target(project, "slide_body:3", repo)
        assert original == "PT body 3"
        await setter("New PT body")
        assert slide.body == "New PT body"

    async def test_invalid_language_returns_none(self) -> None:
        from rag_backend.application.tools.carousel.refine_copy import (
            _resolve_refine_target,
        )

        repo = AsyncMock()
        slide = _slide(1)
        repo.get_slides_by_project = AsyncMock(return_value=[slide])
        project = CarouselProject(topic="T", audience="A", niche="N")
        original, _ = await _resolve_refine_target(project, "slide_heading:1:fr", repo)
        assert original is None
