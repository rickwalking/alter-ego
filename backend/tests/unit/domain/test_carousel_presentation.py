"""Unit tests for carousel presentation contract models and legacy adapters."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
)
from rag_backend.domain.models.carousel_presentation import (
    ActionItem,
    CarouselDraftPackage,
    ClosingSlideCopy,
    ContentSlideCopy,
    CtaSlideCopy,
    FeatureItem,
    InsightItem,
    IntroSlideCopy,
    SlideDraft,
    SlideValidationReport,
    SlideValidationViolation,
    StatItem,
    SummarySlideCopy,
)
from rag_backend.domain.models.carousel_presentation_adapters import (
    adapt_legacy_structured_item,
    detect_translation_shape_mismatch,
    read_legacy_slide_extras,
    resolve_structured_item_icon_name,
)


def _feature(icon_name: str = "target") -> FeatureItem:
    return FeatureItem(icon_name=icon_name, title="Title", body="Body text")


def _summary_copy() -> SummarySlideCopy:
    return SummarySlideCopy(
        heading="Summary",
        body="Overview",
        summary_points=[_feature("target"), _feature("eye"), _feature("brain")],
    )


def _content_features_copy() -> ContentSlideCopy:
    return ContentSlideCopy(
        heading="Idea",
        body="Explanation",
        content_kind="features",
        features=[_feature("chart-column"), _feature("book-open")],
    )


def _closing_copy() -> ClosingSlideCopy:
    return ClosingSlideCopy(
        heading="Actions",
        body="Next steps",
        actions=[
            ActionItem(icon_name="shield-check", title="Audit", body="Weekly scan"),
            ActionItem(icon_name="wrench", title="Patch", body="Apply fixes"),
            ActionItem(icon_name="eye", title="Monitor", body="Watch logs"),
        ],
    )


def _cta_copy(*, heading: str = "Follow") -> CtaSlideCopy:
    return CtaSlideCopy(
        heading=heading,
        body="Creator card",
        creator_name="Pedro Marins",
        creator_handle="pedromarins.ai",
        creator_website="marinssolutions.com",
    )


@pytest.mark.unit
class TestFeatureItemValidation:
    """Scenario: Structured item icons use allowlisted Lucide icon_name values."""

    def test_accepts_allowlisted_icon_name(self) -> None:
        item = FeatureItem(icon_name="chart-column", title="Metric", body="Detail")
        assert item.icon_name == "chart-column"

    def test_rejects_unknown_icon_name(self) -> None:
        with pytest.raises(ValidationError, match="icon_name is not in the Lucide allowlist"):
            FeatureItem(icon_name="rocket-ship", title="Metric", body="Detail")

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            FeatureItem(
                icon_name="target",
                title="Metric",
                body="Detail",
                icon="🎯",
            )


@pytest.mark.unit
class TestContentSlideCopyValidation:
    """Scenario: Content slides enforce content_kind structural rules."""

    def test_requires_matching_structured_field(self) -> None:
        with pytest.raises(ValidationError, match="features is required"):
            ContentSlideCopy(
                heading="Idea",
                body="Explanation",
                content_kind="features",
            )

    def test_forbids_unselected_structured_fields(self) -> None:
        with pytest.raises(ValidationError, match="stats and insight are forbidden"):
            ContentSlideCopy(
                heading="Idea",
                body="Explanation",
                content_kind="features",
                features=[_feature("target"), _feature("eye")],
                stats=[
                    StatItem(
                        icon_name="chart-column",
                        value="80%",
                        label="Accuracy",
                    )
                ],
            )

    def test_accepts_insight_content_kind(self) -> None:
        copy = ContentSlideCopy(
            heading="Insight",
            body="Takeaway",
            content_kind="insight",
            insight=InsightItem(
                icon_name="brain",
                quote="Quote text",
                attribution="Source",
            ),
        )
        assert copy.content_kind == "insight"


@pytest.mark.unit
class TestCarouselDraftPackage:
    """Scenario: Seven-slide draft package uses discriminated bilingual unions."""

    def test_builds_valid_seven_slide_package(self) -> None:
        package = CarouselDraftPackage(
            policy_version="hero_lower_third_v1",
            slides=[
                SlideDraft(
                    slide_index=1,
                    slide_type="intro",
                    presentation_pt=IntroSlideCopy(heading="Hook", body="Subtitle"),
                    presentation_en=IntroSlideCopy(
                        heading="Hook EN",
                        body="Subtitle EN",
                    ),
                ),
                SlideDraft(
                    slide_index=2,
                    slide_type="summary",
                    presentation_pt=_summary_copy(),
                    presentation_en=_summary_copy(),
                ),
                SlideDraft(
                    slide_index=3,
                    slide_type="content",
                    presentation_pt=_content_features_copy(),
                    presentation_en=_content_features_copy(),
                ),
                SlideDraft(
                    slide_index=4,
                    slide_type="content",
                    presentation_pt=_content_features_copy(),
                    presentation_en=_content_features_copy(),
                ),
                SlideDraft(
                    slide_index=5,
                    slide_type="content",
                    presentation_pt=_content_features_copy(),
                    presentation_en=_content_features_copy(),
                ),
                SlideDraft(
                    slide_index=6,
                    slide_type="closing",
                    presentation_pt=_closing_copy(),
                    presentation_en=_closing_copy(),
                ),
                SlideDraft(
                    slide_index=7,
                    slide_type="cta",
                    presentation_pt=_cta_copy(),
                    presentation_en=_cta_copy(heading="Follow EN"),
                ),
            ],
        )
        assert len(package.slides) == 7
        assert package.slides[0].presentation_pt.slide_type == "intro"

    def test_rejects_mismatched_locale_slide_types(self) -> None:
        with pytest.raises(ValidationError, match="slide_type must match"):
            SlideDraft(
                slide_index=1,
                slide_type="intro",
                presentation_pt=IntroSlideCopy(heading="Hook", body="Subtitle"),
                presentation_en=_summary_copy(),
            )


@pytest.mark.unit
class TestSlideValidationReport:
    """Scenario: Validation reports stay consistent with violation lists."""

    def test_invalid_report_requires_violations(self) -> None:
        with pytest.raises(ValidationError, match="invalid reports must contain"):
            SlideValidationReport(
                validation_status="invalid",
                validated_at=datetime.now(tz=UTC),
                blocking=True,
                violations=[],
            )

    def test_valid_report_rejects_violations(self) -> None:
        with pytest.raises(ValidationError, match="valid reports must not contain"):
            SlideValidationReport(
                validation_status="valid",
                validated_at=datetime.now(tz=UTC),
                blocking=False,
                violations=[
                    SlideValidationViolation(
                        code="heading_empty",
                        message="Heading is required",
                    )
                ],
            )


@pytest.mark.unit
class TestLegacyPresentationAdapters:
    """Scenario: Legacy carousel rows remain readable without forced regeneration."""

    def test_resolve_icon_name_prefers_icon_name_then_legacy_icon(self) -> None:
        assert resolve_structured_item_icon_name({"icon_name": "target"}) == "target"
        assert resolve_structured_item_icon_name({"icon": "🎯"}) == "🎯"

    def test_adapt_legacy_structured_item_exposes_icon_name_view(self) -> None:
        adapted = adapt_legacy_structured_item(
            {"icon": "🎯", "title": "Point one", "body": "Detail"}
        )
        assert adapted["icon_name"] == "🎯"
        assert "icon" not in adapted
        assert adapted["title"] == "Point one"

    def test_read_legacy_slide_extras_preserves_translation_en(self) -> None:
        view = read_legacy_slide_extras(
            {
                "features": [{"icon": "✅", "title": "Audit", "body": "Weekly"}],
                "translation_en": {
                    "features": [{"icon": "✅", "title": "Audit EN", "body": "Weekly EN"}]
                },
            }
        )
        features = view["features"]
        assert isinstance(features, list)
        assert features[0]["icon_name"] == "✅"
        translation_en = view["translation_en"]
        assert isinstance(translation_en, dict)
        en_features = translation_en["features"]
        assert isinstance(en_features, list)
        assert en_features[0]["icon_name"] == "✅"

    def test_detect_translation_shape_mismatch_for_features_vs_stats(self) -> None:
        violation = detect_translation_shape_mismatch(
            {
                "features": [
                    {"icon": "🎯", "title": "One", "body": "A"},
                    {"icon": "🔍", "title": "Two", "body": "B"},
                ]
            },
            {
                "stats": [
                    {"value": "80%", "label": "Accuracy", "detail": "Up"},
                    {"value": "3x", "label": "Speed", "detail": "Fast"},
                    {"value": "99%", "label": "Uptime", "detail": "Stable"},
                ]
            },
        )
        assert violation is not None
        assert violation.code == VIOLATION_TRANSLATION_SHAPE_MISMATCH
