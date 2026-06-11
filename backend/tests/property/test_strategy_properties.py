"""Property-based tests for slide layout strategies using Hypothesis.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from rag_backend.application.services.carousel_template.strategies import (
    CtaCenteredStrategy,
    FeatureGridStrategy,
    InsightQuoteStrategy,
    IntroHeroStrategy,
    NumberedListStrategy,
)
from rag_backend.application.services.carousel_template.strategies.hero_content import (
    HeroContentStrategy,
)
from rag_backend.application.services.carousel_template.strategies.stat_card_grid import (
    StatCardGridStrategy,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel import CarouselTheme
from rag_backend.domain.protocols.carousel import _RenderOptions

_PROJECT = CarouselProject(
    topic="Test",
    audience="Testers",
    niche="Testing",
    theme=CarouselTheme.AI_COMPETITION,
)
_PROJECT.creator_name = "Tester"
_PROJECT.creator_handle = "tester"

_THEME = {"primary": "#3b82f6", "accent": "#f59e0b", "background": "#0a0e17"}

_SLIDE_TYPES = st.sampled_from(["intro", "content", "summary", "closing", "cta"])
_TEXT = st.text(min_size=0, max_size=200)
_HEX = st.sampled_from(["#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff"])


@given(
    strategy=st.sampled_from([
        HeroContentStrategy(),
        StatCardGridStrategy(),
        FeatureGridStrategy(),
        InsightQuoteStrategy(),
        NumberedListStrategy(),
        IntroHeroStrategy(),
        CtaCenteredStrategy(),
    ]),
    slide_type=_SLIDE_TYPES,
    heading=_TEXT,
    body=_TEXT,
)
@settings(max_examples=50)
def test_any_text_input_produces_safe_html(strategy, slide_type, heading, body):
    slide = {
        "number": "1",
        "type": slide_type,
        "heading": heading,
        "body": body,
        "stats": [{"value": "X", "label": "Y", "detail": "Z"}],
        "features": [{"icon_name": "target", "title": "T", "body": "B"}],
        "insight": None,
        "summary_points": [],
        "tldr_strip": None,
    }
    result = strategy.render(
        slide, _PROJECT, _THEME, options=_RenderOptions(total_slides=7, language="pt")
    )
    assert isinstance(result, str)
    assert len(result) > 0


@given(
    primary=_HEX,
    accent=_HEX,
    background=_HEX,
)
@settings(max_examples=30)
def test_any_theme_produces_output(primary, accent, background):
    strategy = HeroContentStrategy()
    theme = {"primary": primary, "accent": accent, "background": background}
    slide = {
        "number": "1",
        "type": "content",
        "heading": "Test",
        "body": "Body",
        "stats": [],
        "features": [],
        "insight": None,
        "summary_points": [],
        "tldr_strip": None,
    }
    result = strategy.render(
        slide, _PROJECT, theme, options=_RenderOptions(total_slides=7, language="pt")
    )
    assert isinstance(result, str)


@given(
    total_slides=st.integers(min_value=1, max_value=15),
    slide_number=st.integers(min_value=1, max_value=15),
)
@settings(max_examples=30)
def test_any_slide_count_produces_output(total_slides, slide_number):
    if slide_number > total_slides:
        return
    strategy = HeroContentStrategy()
    slide = {
        "number": str(slide_number),
        "type": "content",
        "heading": "Test",
        "body": "Body",
        "stats": [],
        "features": [],
        "insight": None,
        "summary_points": [],
        "tldr_strip": None,
    }
    result = strategy.render(
        slide, _PROJECT, _THEME, total_slides=total_slides, language="pt"
    )
    assert isinstance(result, str)
    assert f"{slide_number:02d}" in result or str(slide_number) in result


@given(
    language=st.sampled_from(["pt", "en"]),
)
@settings(max_examples=10)
def test_bilingual_rendering_produces_output(language):
    strategy = HeroContentStrategy()
    slide = {
        "number": "1",
        "type": "content",
        "heading": "Test",
        "body": "Body",
        "stats": [],
        "features": [],
        "insight": None,
        "summary_points": [],
        "tldr_strip": None,
    }
    result = strategy.render(slide, _PROJECT, _THEME, total_slides=7, language=language)
    assert isinstance(result, str)
