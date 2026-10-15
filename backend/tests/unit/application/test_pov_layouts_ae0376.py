"""POV layouts, artwork selection, export paths and Radar IA v7 (AE-0376).

Gherkin: tests/features/carousel_pov_layouts.feature
"""

from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import pytest

from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.application.services.carousel.creator_asset_validation import (
    CreatorAssetUpload,
    validate_and_normalize_creator_asset,
)
from rag_backend.application.services.carousel.image_artwork import (
    artwork_slide_numbers,
)
from rag_backend.application.services.carousel.nodes.export import (
    rewrite_asset_paths,
)
from rag_backend.application.services.carousel.nodes.images import (
    filter_image_slides,
)
from rag_backend.application.services.carousel.types import SlideData
from rag_backend.application.services.carousel_template.builder import (
    CarouselTemplateBuilder,
)
from rag_backend.application.services.carousel_template.role_layouts import (
    pov_slide_strategies,
)
from rag_backend.application.services.carousel_template.strategies.cta_follow import (
    CtaFollowStrategy,
)
from rag_backend.application.services.carousel_template.strategies.hook_face import (
    HookFaceStrategy,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    bootstrap_strategies,
)
from rag_backend.application.services.carousel_template.strategies.save_checklist import (
    SaveChecklistStrategy,
    checklist_items,
)
from rag_backend.application.services.carousel_template.strategies.statement import (
    StatementStrategy,
)
from rag_backend.application.services.image_style_strategies import (
    IMAGE_STRATEGY_REGISTRY,
    OpenAIFlatEditorialStrategy,
)
from rag_backend.domain.constants import SUPPORTED_IMAGE_COMBOS
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols.carousel import _RenderOptions
from rag_backend.modules.autopilot.domain.carousel_defaults import SCOUT_IMAGE_STYLES

_THEME = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}
_PHOTO = "assets/creators/abc.webp"


def _pov(**changes: object) -> CarouselProject:
    project = CarouselProject(topic="T", audience="Devs", niche="IA")
    project.content_mode = "pov"
    project.presentation_policy_version = "pov_hook_v1"
    project.slide_count = 9
    project.cta_goal = "send"
    project.creator_handle = "pedromarins.ai"
    project.slide_layout_strategy = "numbered_list"
    for key, value in changes.items():
        setattr(project, key, value)
    return project


def _opts(total: int = 9, language: str = "pt") -> _RenderOptions:
    return _RenderOptions(total_slides=total, language=language)


@pytest.mark.unit
class TestHookFace:
    # Scenario: Hook slide uses the owner's photo
    def test_photo_and_hook(self) -> None:
        project = _pov(hook_asset_id=uuid4(), hook_asset_staged_path=_PHOTO)
        html = HookFaceStrategy().render(
            {"number": "1", "heading": "Pare de pedir código", "body": "Sub"},
            project,
            _THEME,
            options=_opts(),
        )
        assert f'src="{_PHOTO}"' in html
        assert "Pare de pedir código" in html
        assert "images/slide_1.jpg" not in html
        assert "Deslize" in html
        assert "@pedromarins.ai" in html

    # Scenario: Hook slide without a photo
    def test_no_photo(self) -> None:
        html = HookFaceStrategy().render(
            {"number": "1", "heading": "Gancho"}, _pov(), _THEME, options=_opts()
        )
        assert "pov-hook-photo" not in html
        assert "pov-hook-sub" not in html
        assert "Gancho" in html


@pytest.mark.unit
class TestOtherLayouts:
    def test_statement_has_no_artwork(self) -> None:
        html = StatementStrategy().render(
            {"number": "2", "heading": "Tensão", "body": "Corpo"},
            _pov(),
            _THEME,
            options=_opts(),
        )
        assert "slide-artwork" not in html
        assert ">02 / 09<" in html
        assert "pov-statement-body" in html

    def test_statement_without_body(self) -> None:
        html = StatementStrategy().render(
            {"number": "3", "heading": "Só título"}, _pov(), _THEME, options=_opts()
        )
        assert "pov-statement-body" not in html

    # Scenario: Save checklist shows 3 to 5 items
    def test_checklist_caps_at_five(self) -> None:
        points = [{"title": f"Item {i}"} for i in range(6)]
        html = SaveChecklistStrategy().render(
            {"number": "8", "heading": "Salve", "summary_points": points},
            _pov(),
            _THEME,
            options=_opts(),
        )
        assert html.count("pov-check-item") == 5
        assert "Item 5" not in html

    def test_checklist_items_fallbacks(self) -> None:
        assert checklist_items({"actions": [{"body": "Faça X"}, "x", {}]}) == ["Faça X"]
        assert checklist_items({"summary_points": "nope"}) == []

    def test_checklist_without_items_is_a_statement(self) -> None:
        html = SaveChecklistStrategy().render(
            {"number": "8", "heading": "Salve", "body": "B"},
            _pov(),
            _THEME,
            options=_opts(),
        )
        assert "pov-checklist" not in html
        assert "pov-statement-heading" in html

    # Scenario: CTA by goal
    def test_cta_follow_comment(self) -> None:
        html = CtaFollowStrategy().render(
            {"number": "9"}, _pov(cta_goal="comment"), _THEME, options=_opts()
        )
        assert "Discorda? Me diz nos comentários." in html
        assert html.count("marinssolutions.com") == 1
        assert "creator-card" in html
        assert ">09 / 09<" in html

    def test_cta_follow_english_send(self) -> None:
        html = CtaFollowStrategy().render(
            {"number": "9"}, _pov(), _THEME, options=_opts(language="en")
        )
        assert "Send this to someone who needs to hear it." in html


@pytest.mark.unit
class TestRoleLayouts:
    # Scenario: Layout by role
    def test_pov_map(self) -> None:
        assert pov_slide_strategies(_pov(), 9) == {
            1: "hook_face",
            2: "statement",
            3: "statement",
            7: "insight_quote",
            8: "save_checklist",
            9: "cta_follow",
        }

    # Scenario: Radar IA decks keep today's layouts
    def test_radar_has_no_map(self) -> None:
        project = _pov(content_mode="news_analysis")
        assert pov_slide_strategies(project, 7) == {}

    def test_out_of_range_deck_uses_the_default(self) -> None:
        assert pov_slide_strategies(_pov(), 12)[9] == "cta_follow"

    def test_registry_knows_the_pov_layouts(self) -> None:
        names = {item["name"] for item in bootstrap_strategies().list()}
        assert {"hook_face", "statement", "save_checklist", "cta_follow"} <= names

    def test_rendered_pov_deck(self) -> None:
        slides = [
            {"number": str(i), "type": t, "heading": f"Slide {i}", "body": "Corpo"}
            for i, t in enumerate(
                [
                    "intro",
                    "content",
                    "content",
                    "content",
                    "content",
                    "content",
                    "content",
                    "summary",
                    "cta",
                ],
                1,
            )
        ]
        html = CarouselTemplateBuilder.build_carousel_html(
            _pov(),
            slides,
            _THEME,
            strategy_registry=bootstrap_strategies(),
        )
        assert "pov-hook-heading" in html
        assert "pov-statement-heading" in html
        assert "pov-cta-sentence" in html
        assert "images/slide_1.jpg" not in html
        assert "images/slide_2.jpg" not in html
        # point slides keep the format layout (numbered_list -> hero fallback art)
        assert "images/slide_4.jpg" in html
        assert ".pov-solid" in html


def _slide(number: int, slide_type: str) -> SlideData:
    return SlideData(
        slide_number=number,
        slide_type=slide_type,
        heading="H",
        body="B",
        image_prompt="scene",
    )


@pytest.mark.unit
class TestArtwork:
    # Scenario: Only point slides get artwork
    def test_pov_points_only(self) -> None:
        assert artwork_slide_numbers(_pov()) == frozenset({4, 5, 6})
        slides = [_slide(i, "content") for i in range(1, 10)]
        picked = filter_image_slides(slides, artwork_slide_numbers(_pov()))
        assert [s.slide_number for s in picked] == [4, 5, 6]

    # Scenario: Radar IA v4 skips the news and verdict artwork
    def test_v4(self) -> None:
        project = _pov(
            content_mode="news_analysis",
            presentation_policy_version="hero_lower_third_v4",
            slide_count=7,
        )
        assert artwork_slide_numbers(project) == frozenset({1, 3, 4, 5})

    # Scenario: Legacy decks keep the slide-type rule
    def test_legacy(self) -> None:
        project = _pov(presentation_policy_version="hero_lower_third_v3")
        assert artwork_slide_numbers(project) is None
        slides = [_slide(1, "intro"), _slide(7, "cta"), _slide(2, "summary")]
        assert [s.slide_number for s in filter_image_slides(slides, None)] == [1, 2]

    def test_no_prompt_no_artwork(self) -> None:
        slide = _slide(4, "content")
        slide.image_prompt = ""
        assert filter_image_slides([slide], frozenset({4})) == []

    # Scenario: The Radar IA scout never picks the POV preset
    def test_pov_preset(self) -> None:
        assert ("openai", "pov_editorial") in SUPPORTED_IMAGE_COMBOS
        assert (
            IMAGE_STRATEGY_REGISTRY[("openai", "pov_editorial")]
            is OpenAIFlatEditorialStrategy
        )
        assert "pov_editorial" not in SCOUT_IMAGE_STYLES
        assert "flat_editorial" in SCOUT_IMAGE_STYLES


def _png(mode: str) -> bytes:
    from PIL import Image

    buffer = BytesIO()
    color = (10, 20, 30, 0) if mode == "RGBA" else (10, 20, 30)
    Image.new(mode, (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.unit
class TestTransparency:
    # Scenario: Transparent photos keep their transparency
    def test_alpha_is_kept(self) -> None:
        from PIL import Image

        normalized = validate_and_normalize_creator_asset(
            CreatorAssetUpload(content=_png("RGBA"), declared_mime="image/png")
        )
        with Image.open(BytesIO(normalized.webp_bytes)) as image:
            assert image.mode == "RGBA"

    def test_opaque_stays_rgb(self) -> None:
        from PIL import Image

        normalized = validate_and_normalize_creator_asset(
            CreatorAssetUpload(content=_png("RGB"), declared_mime="image/png")
        )
        with Image.open(BytesIO(normalized.webp_bytes)) as image:
            assert image.mode == "RGB"


@pytest.mark.unit
def test_export_rewrites_images_and_assets() -> None:
    """Scenario: Exported slides find staged assets."""
    html = (
        '<img src="images/slide_1.jpg"/><img src=\'assets/creators/a.webp\'/>'
        '<div style="background: url(\'images/x.jpg\')"></div>'
        '<img src="https://cdn/x.png"/>'
    )
    out = rewrite_asset_paths(html, "../")
    assert 'src="../images/slide_1.jpg"' in out
    assert "src='../assets/creators/a.webp'" in out
    assert "url('../images/x.jpg')" in out
    assert 'src="https://cdn/x.png"' in out
    assert 'src="../../assets/' in rewrite_asset_paths('<img src="assets/a"/>', "../../")


@pytest.mark.unit
class TestRadarV7Prompts:
    def test_hook_from_sources_only(self) -> None:
        text, _ = render_prompt(
            "carousel",
            "hook",
            variables={"topic": "Gemini 4", "sources": "fonte"},
            version="v7",
        )
        assert "Todo mundo falou de X. Ninguém falou disso." in text
        assert "Nunca invente números" in text

    def test_outline_angle_and_roles(self) -> None:
        roles = ["hook", "news", "impact", "impact", "impact", "verdict", "cta"]
        text, _ = render_prompt(
            "carousel",
            "outline",
            variables={"roles": roles, "slide_count": 7},
            version="v7",
        )
        assert "No máximo UM slide sobre o que aconteceu" in text
        assert "7. cta" in text
        assert "Não atribua opinião ou experiência pessoal" in text

    @pytest.mark.parametrize(
        ("role", "marker"),
        [
            ("news", "ONLY slide about what happened"),
            ("impact", "changes for the reader"),
            ("verdict", "Do not attribute an opinion"),
            ("hook", 'EXACTLY: "Gancho"'),
        ],
    )
    def test_content_by_role(self, role: str, marker: str) -> None:
        text, _ = render_prompt(
            "carousel",
            "content",
            variables={"role": role, "hook_text": "Gancho"},
            version="v7",
        )
        assert marker in text
        assert "Never invent numbers" in text
