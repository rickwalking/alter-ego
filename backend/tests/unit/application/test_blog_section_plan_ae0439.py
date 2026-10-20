"""AE-0439 (QA F-07): the section count prefers the real deck size and a
Radar IA create stores a slide count (CTA included, per ADR-0025).

Gherkin: tests/features/blog_carousel_minors_ae0439.feature
  - Scenario: A blog from a 7-slide deck without a stored slide_count gets 7 sections
  - Scenario: A Radar IA create without slide_count stores 7
  - Scenario: An explicit Radar IA slide_count of 8 is kept
"""

from __future__ import annotations

import pytest

from rag_backend.api.schemas.carousel_content_mode import ContentModeRequestFields
from rag_backend.application.services.blog.blog_section_plan import (
    SectionCountSource,
    resolve_section_count,
)
from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_NEWS_ANALYSIS,
    CONTENT_MODE_POV,
    NEWS_SLIDE_COUNT_MIN,
    POV_SLIDE_COUNT_DEFAULT,
)


@pytest.mark.unit
class TestResolveSectionCount:
    def test_a_stored_slide_count_wins(self) -> None:
        source = SectionCountSource(slide_count=8, deck_slide_count=7)
        assert resolve_section_count(source) == 8

    def test_the_real_deck_size_beats_the_legacy_config(self) -> None:
        """Scenario: A 7-slide deck without a stored count gets 7 sections."""
        source = SectionCountSource(
            slide_count=None,
            deck_slide_count=7,
            slides_config="1 intro, 3 content, 1 closing, 1 cta",
            content_mode=CONTENT_MODE_NEWS_ANALYSIS,
        )
        assert resolve_section_count(source) == 7

    def test_the_legacy_config_still_sizes_a_deckless_project(self) -> None:
        source = SectionCountSource(slides_config="2 intro, 3 content, 1 closing")
        assert resolve_section_count(source) == 6

    def test_the_mode_default_is_the_last_resort(self) -> None:
        assert resolve_section_count(SectionCountSource()) == NEWS_SLIDE_COUNT_MIN
        assert (
            resolve_section_count(
                SectionCountSource(content_mode=CONTENT_MODE_POV)
            )
            == POV_SLIDE_COUNT_DEFAULT
        )

    def test_a_zero_deck_is_ignored(self) -> None:
        source = SectionCountSource(deck_slide_count=0)
        assert resolve_section_count(source) == NEWS_SLIDE_COUNT_MIN


@pytest.mark.unit
class TestResolvedSlideCount:
    def test_a_news_create_without_a_count_stores_seven(self) -> None:
        """Scenario: A Radar IA create without slide_count stores 7."""
        fields = ContentModeRequestFields(content_mode=CONTENT_MODE_NEWS_ANALYSIS)
        assert fields.resolved_slide_count() == 7

    def test_an_explicit_news_count_is_kept(self) -> None:
        """Scenario: An explicit Radar IA slide_count of 8 is kept."""
        fields = ContentModeRequestFields(
            content_mode=CONTENT_MODE_NEWS_ANALYSIS, slide_count=8
        )
        assert fields.resolved_slide_count() == 8

    def test_pov_keeps_its_default(self) -> None:
        fields = ContentModeRequestFields(content_mode=CONTENT_MODE_POV)
        assert fields.resolved_slide_count() == POV_SLIDE_COUNT_DEFAULT
