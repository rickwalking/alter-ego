"""Unit tests for the slide-type dispatch table (lightweight Strategy).

Covers AE-0045 Feature: Dispatch Table for Slide Types. Each registered
builder is exercised independently and the unknown-slide-type fallback to
the CTA builder is asserted (mutation-killing for the dict-dispatch default).
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.malformed_draft_builders import (
    _BUILDERS,
    _build_closing,
    _build_content,
    _build_cta,
    _build_intro,
    _build_summary,
    build_locale_presentation,
)
from rag_backend.domain.constants.carousel import (
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.carousel_presentation import CONTENT_KIND_FEATURES


def _item_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    """Return the list-of-dicts stored under key, asserting its shape."""
    value = payload[key]
    assert isinstance(value, list)
    items: list[dict[str, object]] = []
    for entry in value:
        assert isinstance(entry, dict)
        items.append(entry)
    return items


@pytest.mark.unit
class TestDispatchTableRegistration:
    """Gherkin Feature: Dispatch Table for Slide Types (registration)."""

    def test_all_five_builders_are_registered(self) -> None:
        """THEN every known slide type maps to its dedicated builder."""
        assert _BUILDERS[SLIDE_TYPE_INTRO] is _build_intro
        assert _BUILDERS[SLIDE_TYPE_SUMMARY] is _build_summary
        assert _BUILDERS[SLIDE_TYPE_CONTENT] is _build_content
        assert _BUILDERS[SLIDE_TYPE_CLOSING] is _build_closing
        assert _BUILDERS[SLIDE_TYPE_CTA] is _build_cta

    def test_dispatch_table_has_no_unexpected_entries(self) -> None:
        """THEN the table contains exactly the five known slide types."""
        assert set(_BUILDERS) == {
            SLIDE_TYPE_INTRO,
            SLIDE_TYPE_SUMMARY,
            SLIDE_TYPE_CONTENT,
            SLIDE_TYPE_CLOSING,
            SLIDE_TYPE_CTA,
        }


@pytest.mark.unit
class TestBuildLocalePresentationDispatch:
    """Gherkin Feature: Dispatch Table for Slide Types (dispatch behavior)."""

    def test_unknown_slide_type_falls_back_to_cta(self) -> None:
        """Scenario: unknown slide_type falls back to CTA.

        Given an unknown slide_type "bogus"
        When build_locale_presentation is called
        Then the CTA builder is used (slide_type is normalized to cta).
        """
        result = build_locale_presentation(
            "bogus",
            {"title": "Follow me", "body": "Tap the link"},
        )
        assert result["slide_type"] == SLIDE_TYPE_CTA
        # CTA-only fields prove the CTA builder produced the payload.
        assert "creator_name" in result
        assert "creator_handle" in result
        assert "creator_website" in result

    def test_intro_dispatch_returns_intro_structure(self) -> None:
        """Scenario: intro builder returns correct structure.

        Given slide_type "intro"
        When build_locale_presentation is called
        Then result has slide_type "intro" and heading.
        """
        result = build_locale_presentation(
            SLIDE_TYPE_INTRO,
            {"heading": "Big news", "subtitle": "Read on"},
        )
        assert result["slide_type"] == SLIDE_TYPE_INTRO
        assert result["heading"] == "Big news"

    def test_dispatch_routes_each_known_type_to_its_builder(self) -> None:
        """THEN each known slide_type yields its own slide_type in the payload."""
        for slide_type in (
            SLIDE_TYPE_INTRO,
            SLIDE_TYPE_SUMMARY,
            SLIDE_TYPE_CONTENT,
            SLIDE_TYPE_CLOSING,
            SLIDE_TYPE_CTA,
        ):
            result = build_locale_presentation(slide_type, {})
            assert result["slide_type"] == slide_type


@pytest.mark.unit
class TestBuildIntro:
    """Independent unit tests for the intro builder."""

    def test_intro_prefers_subtitle_over_body(self) -> None:
        """THEN subtitle wins over body for the intro slide body."""
        result = _build_intro(
            {"heading": "H", "subtitle": "Sub", "body": "Body"}, None, 0
        )
        assert result == {"slide_type": SLIDE_TYPE_INTRO, "heading": "H", "body": "Sub"}

    def test_intro_falls_back_to_body_when_no_subtitle(self) -> None:
        """THEN body is used when subtitle is absent."""
        result = _build_intro({"heading": "H", "body": "Body"}, None, 0)
        assert result["body"] == "Body"

    def test_intro_includes_tldr_strip_when_provided(self) -> None:
        """THEN a non-empty tldr_strip is attached to the payload."""
        result = _build_intro({"heading": "H"}, "tl;dr", 0)
        assert result["tldr_strip"] == "tl;dr"

    def test_intro_omits_tldr_strip_when_none(self) -> None:
        """THEN tldr_strip is absent when not provided (mutation-killing)."""
        result = _build_intro({"heading": "H"}, None, 0)
        assert "tldr_strip" not in result


@pytest.mark.unit
class TestBuildSummary:
    """Independent unit tests for the summary builder."""

    def test_summary_caps_points_at_three(self) -> None:
        """THEN only the first three points are kept."""
        points = [{"title": f"P{i}", "body": "b"} for i in range(5)]
        result = _build_summary({"heading": "H", "points": points}, None, 0)
        assert len(_item_list(result, "summary_points")) == 3

    def test_summary_reads_summary_points_alias(self) -> None:
        """THEN summary_points is read when points is absent."""
        result = _build_summary(
            {"heading": "H", "summary_points": [{"title": "P", "body": "b"}]},
            None,
            0,
        )
        assert len(_item_list(result, "summary_points")) == 1

    def test_summary_icon_offset_rotates_default_icon(self) -> None:
        """THEN icon_offset shifts the default icon assignment."""
        base = _build_summary({"points": [{"title": "P", "body": "b"}]}, None, 0)
        shifted = _build_summary({"points": [{"title": "P", "body": "b"}]}, None, 1)
        assert (
            _item_list(base, "summary_points")[0]["icon_name"]
            != _item_list(shifted, "summary_points")[0]["icon_name"]
        )


@pytest.mark.unit
class TestBuildContent:
    """Independent unit tests for the content builder."""

    def test_content_sets_features_content_kind(self) -> None:
        """THEN the content builder marks the slide as a features kind."""
        result = _build_content({"heading": "H", "body": "B"}, None, 0)
        assert result["content_kind"] == CONTENT_KIND_FEATURES

    def test_content_caps_features_at_three(self) -> None:
        """THEN only the first three features are kept."""
        features = [{"title": f"F{i}", "body": "b"} for i in range(5)]
        result = _build_content({"features": features}, None, 0)
        assert len(_item_list(result, "features")) == 3


@pytest.mark.unit
class TestBuildClosing:
    """Independent unit tests for the closing builder."""

    def test_closing_caps_actions_at_four(self) -> None:
        """THEN only the first four actions are kept."""
        actions = [{"title": f"A{i}", "body": "b"} for i in range(6)]
        result = _build_closing({"actions": actions}, None, 0)
        assert len(_item_list(result, "actions")) == 4

    def test_closing_falls_back_to_features_for_actions(self) -> None:
        """THEN features are used as actions when actions is absent."""
        result = _build_closing({"features": [{"title": "A", "body": "b"}]}, None, 0)
        assert len(_item_list(result, "actions")) == 1


@pytest.mark.unit
class TestBuildCta:
    """Independent unit tests for the CTA builder."""

    def test_cta_prefers_title_then_heading(self) -> None:
        """THEN the CTA heading prefers title over heading."""
        result = _build_cta({"title": "T", "heading": "H"}, None, 0)
        assert result["heading"] == "T"

    def test_cta_prefers_cta_prefixed_creator_fields(self) -> None:
        """THEN cta_-prefixed creator fields win over plain creator fields."""
        result = _build_cta(
            {
                "cta_creator_name": "CtaName",
                "creator_name": "PlainName",
                "cta_handle": "@cta",
                "creator_handle": "@plain",
                "cta_website": "cta.dev",
                "creator_website": "plain.dev",
            },
            None,
            0,
        )
        assert result["creator_name"] == "CtaName"
        assert result["creator_handle"] == "@cta"
        assert result["creator_website"] == "cta.dev"
