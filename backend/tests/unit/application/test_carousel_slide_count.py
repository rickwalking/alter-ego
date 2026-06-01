"""Unit tests for slide_count_from_config."""

import pytest

from rag_backend.application.services.carousel.types import slide_count_from_config


@pytest.mark.unit
class TestSlideCountFromConfig:
    """Tests for slide_count_from_config()."""

    def test_n_slides_format(self):
        assert slide_count_from_config("7_slides") == 7

    def test_n_slides_format_6(self):
        assert slide_count_from_config("6_slides") == 6

    def test_comma_format(self):
        assert slide_count_from_config("1 intro, 3 content, 1 closing, 1 cta") == 6

    def test_comma_format_alt(self):
        assert slide_count_from_config("1 intro, 2 content, 1 closing, 1 cta") == 5

    def test_fallback_to_max_slides(self):
        assert slide_count_from_config("invalid") == 7

    def test_empty_string(self):
        assert slide_count_from_config("") == 7

    def test_extra_whitespace(self):
        assert slide_count_from_config("  7_slides  ") == 7

    def test_mixed_case(self):
        assert slide_count_from_config("6_SLIDES") == 6
