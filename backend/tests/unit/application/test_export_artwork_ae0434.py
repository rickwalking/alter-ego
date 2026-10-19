"""The template only references artwork the images phase planned (AE-0434).

Gherkin: tests/features/carousel_export_artwork_ae0434.feature
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from rag_backend.application.services.carousel.image_artwork import (
    artwork_slide_numbers,
)
from rag_backend.application.services.carousel.nodes.export import (
    rewrite_asset_paths,
)
from rag_backend.application.services.carousel.nodes.images import (
    filter_image_slides,
)
from rag_backend.application.services.carousel.types import SlideData, SlideDict
from rag_backend.application.services.carousel_template.builder import (
    CarouselTemplateBuilder,
)
from rag_backend.application.services.carousel_template.lower_third_shell import (
    LowerThirdConfig,
    artwork_enabled,
    render_lower_third_shell,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    bootstrap_strategies,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.external.playwright_artwork_check import (
    missing_artwork_violations,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "ae0430_carousel_5344_content_gate.json"
)
_THEME = {
    "primary": "#00ff88",
    "accent": "#ff00aa",
    "background": "#0a0a0a",
    "mode": "dark",
}
_V4 = "hero_lower_third_v4"
_SLIDE_MARKER = 'class="ig-slide-inner"'
_ARTWORK_IMG = re.compile(r'<div class="slide-artwork">\s*<img src="([^"]+)"')
_NO_ARTWORK = 'class="slide-artwork slide-artwork-none"'
_TYPES_7 = ("intro", "summary", "content", "content", "content", "closing", "cta")
_TYPES_8 = (*_TYPES_7[:5], "content", "closing", "cta")


def _project(version: str = _V4, slide_count: int = 7) -> CarouselProject:
    project = CarouselProject(topic="Grok Bot", audience="Devs", niche="IA")
    project.content_mode = "news_analysis"
    project.presentation_policy_version = version
    project.slide_count = slide_count
    project.creator_handle = "pedromarins.ai"
    return project


def _prod_slides(language: str = "pt") -> list[SlideDict]:
    """The 7 localized slides of prod carousel 5344b6c6."""
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    slides: list[SlideDict] = []
    for item in data["localized_slides"]:
        copy = item[f"presentation_{language}"]
        slides.append({
            "number": str(item["slide_index"]),
            "type": item["slide_type"],
            "heading": copy.get("heading", ""),
            "body": copy.get("body", ""),
            "features": copy.get("features"),
            "summary_points": copy.get("summary_points"),
            "tldr_strip": copy.get("tldr_strip"),
        })
    return slides


def _synthetic_slides(types: tuple[str, ...]) -> list[SlideDict]:
    return [
        {"number": str(i), "type": t, "heading": f"H{i}", "body": f"B{i}"}
        for i, t in enumerate(types, 1)
    ]


def _render(
    project: CarouselProject, slides: list[SlideDict], language: str = "pt"
) -> str:
    return CarouselTemplateBuilder.build_carousel_html(
        project,
        slides,
        _THEME,
        language=language,
        strategy_registry=bootstrap_strategies(),
    )


def _chunks(html: str) -> list[str]:
    return html.split(_SLIDE_MARKER)[1:]


def _artwork_slides(html: str) -> set[int]:
    return {n for n, c in enumerate(_chunks(html), 1) if _ARTWORK_IMG.search(c)}


def _planned(project: CarouselProject, slides: list[SlideDict]) -> set[int]:
    data = [
        SlideData(
            slide_number=int(s["number"]),
            slide_type=str(s["type"]),
            heading="H",
            body="B",
            image_prompt="scene",
        )
        for s in slides
    ]
    return {
        s.slide_number
        for s in filter_image_slides(data, artwork_slide_numbers(project))
    }


def _write_images(root: Path, numbers: set[int]) -> None:
    images = root / "images"
    images.mkdir(parents=True, exist_ok=True)
    for number in numbers:
        (images / f"slide_{number}.jpg").write_bytes(b"jpg")


@pytest.mark.unit
class TestProdDeck5344:
    # Scenario: Summary and closing slides without images export
    def test_html_references_only_planned_artwork(self) -> None:
        html = _render(_project(), _prod_slides())
        assert _artwork_slides(html) == {1, 3, 4, 5}
        assert "images/slide_2.jpg" not in html
        assert "images/slide_6.jpg" not in html

    # Scenario: Summary and closing slides without images export
    def test_unillustrated_slides_render_gradient_region(self) -> None:
        chunks = _chunks(_render(_project(), _prod_slides()))
        assert _NO_ARTWORK in chunks[1]
        assert _NO_ARTWORK in chunks[5]
        assert "summary-grid" in chunks[1]
        assert all(_NO_ARTWORK not in chunks[i] for i in (0, 2, 3, 4))

    # Scenario: Summary and closing slides without images export
    def test_preflight_passes_with_only_planned_images(self, tmp_path: Path) -> None:
        _write_images(tmp_path, {1, 3, 4, 5})
        html = rewrite_asset_paths(_render(_project(), _prod_slides()), "../")
        lang_dir = tmp_path / "pt"
        lang_dir.mkdir()
        assert missing_artwork_violations(html, lang_dir) == ()


@pytest.mark.unit
class TestImagesPhaseAgreesWithTemplate:
    # Scenario Outline: The images phase and the template agree on artwork slides
    @pytest.mark.parametrize(
        ("types", "language"),
        [(_TYPES_7, "pt"), (_TYPES_8, "pt"), (_TYPES_7, "en")],
    )
    def test_artwork_matches_plan(self, types: tuple[str, ...], language: str) -> None:
        project = _project(slide_count=len(types))
        slides = _synthetic_slides(types)
        html = _render(project, slides, language)
        assert _artwork_slides(html) == _planned(project, slides)

    # Scenario: Fixed contracts keep artwork on every lower-third slide
    def test_fixed_contract_keeps_every_artwork(self) -> None:
        project = _project("hero_lower_third_v3")
        slides = _synthetic_slides(_TYPES_7)
        html = _render(project, slides)
        assert _artwork_slides(html) == {1, 2, 3, 4, 5, 6}
        assert _NO_ARTWORK not in html
        assert _artwork_slides(html) == _planned(project, slides)


@pytest.mark.unit
class TestLowerThirdShell:
    # Scenario: An owner-chosen GrokBot cover still renders on a slide without planned artwork
    def test_explicit_cover_wins(self) -> None:
        html = render_lower_third_shell(
            LowerThirdConfig(
                slide_number=2,
                total_slides=7,
                copy_inner_html="x",
                artwork_src="assets/cover.jpg",
                show_artwork=False,
            )
        )
        assert 'src="assets/cover.jpg"' in html
        assert _NO_ARTWORK not in html

    def test_hidden_artwork_has_no_image(self) -> None:
        html = render_lower_third_shell(
            LowerThirdConfig(
                slide_number=2, total_slides=7, copy_inner_html="x", show_artwork=False
            )
        )
        assert _NO_ARTWORK in html
        assert "<img" not in html

    def test_artwork_enabled_defaults_true(self) -> None:
        assert artwork_enabled(None) is True
        assert artwork_enabled({"total_slides": 7}) is True
        assert artwork_enabled({"artwork": False}) is False
