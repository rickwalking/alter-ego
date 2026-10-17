"""Radar IA quick fixes (AE-0372).

Gherkin: tests/features/radar_ia_quick_fixes.feature
"""

from __future__ import annotations

import pytest

from rag_backend.api.schemas.carousel import CarouselProjectCreate
from rag_backend.application.services.carousel_template.builder import (
    CarouselTemplateBuilder,
)
from rag_backend.application.services.carousel_template.cta_copy import (
    cta_copy,
    handle_with_at,
)
from rag_backend.application.services.carousel_template.lower_third_shell import (
    LowerThirdConfig,
    render_lower_third_shell,
)
from rag_backend.application.services.carousel_template.slide_number import (
    format_slide_counter,
)
from rag_backend.application.services.carousel_template.slides import (
    _render_content_slide,
    _render_cta_slide,
)
from rag_backend.application.services.carousel_template.strategies.cta import (
    CtaCenteredStrategy,
)
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.application.services.carousel_template.strategies.intro import (
    IntroHeroStrategy,
)
from rag_backend.domain.constants import IMAGE_STYLE_FLAT_EDITORIAL
from rag_backend.domain.constants.carousel_cta import (
    CTA_GOAL_COMMENT,
    CTA_GOAL_SEND,
)
from rag_backend.domain.protocols.carousel import _RenderOptions
from rag_backend.modules.autopilot.domain.carousel_defaults import DEFAULT_IMAGE_STYLE

_FOLLOW_PT = "Siga @pedromarins.ai: eu traduzo IA em decisões reais."
_FOLLOW_EN = "Follow @pedromarins.ai: I turn AI into real decisions."
_OLD_PT = "Siga para mais conteúdo como esse"


@pytest.mark.unit
class TestSwipeHint:
    # Scenario: Portuguese swipe hint
    def test_pt_intro_says_deslize(self, sample_project, sample_theme) -> None:
        html = IntroHeroStrategy().render(
            {"number": "1", "heading": "Gancho", "body": "Sub"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "Deslize →" in html
        assert "Swipe" not in html

    # Scenario: English swipe hint stays English
    def test_en_intro_says_swipe(self, sample_project, sample_theme) -> None:
        html = IntroHeroStrategy().render(
            {"number": "1", "heading": "Hook", "body": "Sub"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="en"),
        )
        assert "Swipe →" in html
        assert "Deslize" not in html

    def test_slide_two_swipe_follows_the_locale(
        self, sample_project, sample_theme
    ) -> None:
        slide = {"number": "2", "heading": "Resumo", "body": "Corpo"}
        pt = HeroContentStrategy().render(
            slide,
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        en = HeroContentStrategy().render(
            slide,
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="en"),
        )
        assert "Deslize →" in pt
        assert "Swipe →" in en

    def test_other_slides_have_no_swipe(self, sample_project, sample_theme) -> None:
        html = HeroContentStrategy().render(
            {"number": "3", "heading": "Ponto", "body": "Corpo"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert "s1-swipe" not in html


@pytest.mark.unit
class TestSlideCounter:
    # Scenario Outline: Slide counter is zero-padded to two digits
    @pytest.mark.parametrize(
        ("total", "number", "expected"),
        [(7, "3", "03 / 07"), (10, "10", "10 / 10"), (10, 9, "09 / 10")],
    )
    def test_counter_is_padded(self, total: int, number: str, expected: str) -> None:
        assert format_slide_counter(number, total) == expected

    # Scenario: A missing slide number falls back to slide 1
    @pytest.mark.parametrize("number", ["", "abc", "0", "-2"])
    def test_invalid_number_is_slide_one(self, number: str) -> None:
        assert format_slide_counter(number, 7) == "01 / 07"

    def test_shell_renders_ten_of_ten(self) -> None:
        html = render_lower_third_shell(
            LowerThirdConfig(slide_number="10", total_slides=10, copy_inner_html="")
        )
        assert ">10 / 10<" in html
        assert "010" not in html

    def test_shell_without_counter(self) -> None:
        html = render_lower_third_shell(
            LowerThirdConfig(
                slide_number="1",
                total_slides=10,
                copy_inner_html="",
                include_counter=False,
            )
        )
        assert "slide-hero-number" not in html

    def test_legacy_content_slide_counter(self, sample_theme) -> None:
        html = _render_content_slide(
            {"number": 10, "heading": "H", "body": "B"}, sample_theme, 10
        )
        assert ">10 / 10<" in html

    def test_cta_counter_without_number(self, sample_project, sample_theme) -> None:
        html = CtaCenteredStrategy().render(
            {"type": "cta"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert ">01 / 07<" in html


@pytest.mark.unit
class TestCaptionV7:
    # Scenario: Caption v7 keeps hashtags short and the CTA single
    def test_caption_prompt_is_v7(self, sample_project) -> None:
        prompt = CarouselTemplateBuilder.build_caption_prompt(
            sample_project, [(1, "Pare de pedir código pra IA"), (2, "O contexto")]
        )
        assert "Slide 1: Pare de pedir código pra IA" in prompt
        assert "De 3 a 5 hashtags" in prompt
        assert "UMA única chamada para ação" in prompt
        assert "Linha 1: repita o gancho do slide 1" in prompt
        assert 'Nunca peça "salve" e "compartilhe" juntos' in prompt
        assert "12-18" not in prompt
        assert "Objetivo do CTA: follow" in prompt

    def test_caption_prompt_forbids_invented_claims(self, sample_project) -> None:
        prompt = CarouselTemplateBuilder.build_caption_prompt(
            sample_project, [(1, "X")]
        )
        assert "Não invente números" in prompt


@pytest.mark.unit
class TestCtaCopy:
    # Scenario: CTA slide uses the follow variant in Portuguese
    def test_pt_cta_slide(self, sample_project, sample_theme) -> None:
        sample_project.creator_handle = "pedromarins.ai"
        html = CtaCenteredStrategy().render(
            {"number": "7", "type": "cta"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="pt"),
        )
        assert _FOLLOW_PT in html
        assert _OLD_PT not in html

    # Scenario: CTA slide uses the follow variant in English
    def test_en_cta_slide(self, sample_project, sample_theme) -> None:
        sample_project.creator_handle = "@pedromarins.ai"
        html = CtaCenteredStrategy().render(
            {"number": "7", "type": "cta"},
            sample_project,
            sample_theme,
            options=_RenderOptions(total_slides=7, language="en"),
        )
        assert _FOLLOW_EN in html
        assert "@@" not in html

    def test_legacy_cta_slide_uses_follow_copy(self, sample_theme) -> None:
        html = _render_cta_slide({"number": 7}, sample_theme, "pt", 7, None)
        assert _FOLLOW_PT in html

    def test_goal_variants(self) -> None:
        assert (
            cta_copy(CTA_GOAL_SEND, "pt", "x") == "Manda pra quem precisa ouvir isso."
        )
        assert cta_copy(CTA_GOAL_COMMENT, "en", "x") == (
            "Disagree? Tell me in the comments."
        )

    def test_unknown_goal_falls_back_to_follow(self) -> None:
        assert cta_copy("dance", "pt", "pedromarins.ai") == _FOLLOW_PT
        assert cta_copy(None, "pt", "pedromarins.ai") == _FOLLOW_PT

    def test_handle_with_at(self) -> None:
        assert handle_with_at("a") == "@a"
        assert handle_with_at("@a") == "@a"


@pytest.mark.unit
class TestImageDefaults:
    # Scenario: Missing image style falls back to flat editorial
    def test_api_default_is_flat_editorial(self) -> None:
        request = CarouselProjectCreate(topic="IA", audience="Devs", niche="IA")
        assert request.image_style == IMAGE_STYLE_FLAT_EDITORIAL

    # Scenario: The autopilot defaults to flat editorial
    def test_autopilot_default_is_flat_editorial(self) -> None:
        assert DEFAULT_IMAGE_STYLE == IMAGE_STYLE_FLAT_EDITORIAL
