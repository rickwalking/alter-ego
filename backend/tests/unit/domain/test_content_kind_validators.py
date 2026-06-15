"""Isolated unit tests for the content_kind dispatch validators (AE-0046).

These tests exercise the dispatch-based validator functions and the
``_VALIDATORS`` table directly, independently of the ``ContentSlideCopy``
Pydantic model, so each validator is verified in isolation.

Gherkin reference (see ticket AE-0046 "Dispatch-Based Validation"):
  - features validator catches missing features
  - features validator catches forbidden stats
  - insight validator succeeds
  - unknown content_kind passes through
"""

from __future__ import annotations

import pytest

from rag_backend.domain.constants.carousel_presentation import (
    CONTENT_KIND_FEATURES,
    CONTENT_KIND_INSIGHT,
    CONTENT_KIND_STATS,
    ERR_FEATURES_COUNT,
    ERR_FEATURES_FORBIDDEN_FIELDS,
    ERR_FEATURES_REQUIRED,
    ERR_INSIGHT_FORBIDDEN_FIELDS,
    ERR_INSIGHT_REQUIRED,
    ERR_STATS_COUNT,
    ERR_STATS_FORBIDDEN_FIELDS,
    ERR_STATS_REQUIRED,
)
from rag_backend.domain.models.carousel_presentation import (
    _VALIDATORS,
    ContentKindValidationContext,
    FeatureItem,
    InsightItem,
    StatItem,
    _validate_features_content,
    _validate_insight_content,
    _validate_stats_content,
)


def _feature(icon_name: str = "target") -> FeatureItem:
    return FeatureItem(icon_name=icon_name, title="Title", body="Body text")


def _stat(icon_name: str = "chart-column") -> StatItem:
    return StatItem(icon_name=icon_name, value="80%", label="Accuracy")


def _insight() -> InsightItem:
    return InsightItem(icon_name="brain", quote="Quote text", attribution="Source")


@pytest.mark.unit
class TestFeaturesValidator:
    """Scenario: features validator enforces presence, count and exclusivity."""

    def test_accepts_valid_features(self) -> None:
        ctx: ContentKindValidationContext = {"features": [_feature(), _feature("eye")]}
        # Should not raise.
        _validate_features_content(ctx)

    def test_accepts_features_at_max_bound(self) -> None:
        ctx: ContentKindValidationContext = {
            "features": [
                _feature(),
                _feature("eye"),
                _feature("brain"),
                _feature("book-open"),
            ]
        }
        # Should not raise.
        _validate_features_content(ctx)

    def test_rejects_missing_features(self) -> None:
        # Scenario: features validator catches missing features.
        with pytest.raises(ValueError, match=ERR_FEATURES_REQUIRED):
            _validate_features_content({"features": None})

    def test_rejects_too_few_features(self) -> None:
        with pytest.raises(ValueError, match=ERR_FEATURES_COUNT):
            _validate_features_content({"features": [_feature()]})

    def test_rejects_too_many_features(self) -> None:
        with pytest.raises(ValueError, match=ERR_FEATURES_COUNT):
            _validate_features_content({
                "features": [
                    _feature(),
                    _feature("eye"),
                    _feature("brain"),
                    _feature("book-open"),
                    _feature("wrench"),
                ]
            })

    def test_rejects_forbidden_stats(self) -> None:
        # Scenario: features validator catches forbidden stats.
        with pytest.raises(ValueError, match=ERR_FEATURES_FORBIDDEN_FIELDS):
            _validate_features_content({
                "features": [_feature(), _feature("eye")],
                "stats": [_stat()],
            })

    def test_rejects_forbidden_insight(self) -> None:
        with pytest.raises(ValueError, match=ERR_FEATURES_FORBIDDEN_FIELDS):
            _validate_features_content({
                "features": [_feature(), _feature("eye")],
                "insight": _insight(),
            })


@pytest.mark.unit
class TestStatsValidator:
    """Scenario: stats validator enforces presence, exact count and exclusivity."""

    def test_accepts_valid_stats(self) -> None:
        ctx: ContentKindValidationContext = {
            "stats": [_stat(), _stat("eye"), _stat("brain")]
        }
        # Should not raise.
        _validate_stats_content(ctx)

    def test_rejects_missing_stats(self) -> None:
        with pytest.raises(ValueError, match=ERR_STATS_REQUIRED):
            _validate_stats_content({"stats": None})

    def test_rejects_wrong_stat_count(self) -> None:
        with pytest.raises(ValueError, match=ERR_STATS_COUNT):
            _validate_stats_content({"stats": [_stat(), _stat("eye")]})

    def test_rejects_forbidden_features(self) -> None:
        with pytest.raises(ValueError, match=ERR_STATS_FORBIDDEN_FIELDS):
            _validate_stats_content({
                "stats": [_stat(), _stat("eye"), _stat("brain")],
                "features": [_feature()],
            })

    def test_rejects_forbidden_insight(self) -> None:
        with pytest.raises(ValueError, match=ERR_STATS_FORBIDDEN_FIELDS):
            _validate_stats_content({
                "stats": [_stat(), _stat("eye"), _stat("brain")],
                "insight": _insight(),
            })


@pytest.mark.unit
class TestInsightValidator:
    """Scenario: insight validator enforces presence and exclusivity."""

    def test_accepts_valid_insight(self) -> None:
        # Scenario: insight validator succeeds.
        # Should not raise.
        _validate_insight_content({"insight": _insight()})

    def test_rejects_missing_insight(self) -> None:
        with pytest.raises(ValueError, match=ERR_INSIGHT_REQUIRED):
            _validate_insight_content({"insight": None})

    def test_rejects_forbidden_features(self) -> None:
        with pytest.raises(ValueError, match=ERR_INSIGHT_FORBIDDEN_FIELDS):
            _validate_insight_content({
                "insight": _insight(),
                "features": [_feature()],
            })

    def test_rejects_forbidden_stats(self) -> None:
        with pytest.raises(ValueError, match=ERR_INSIGHT_FORBIDDEN_FIELDS):
            _validate_insight_content({
                "insight": _insight(),
                "stats": [_stat()],
            })


@pytest.mark.unit
class TestValidatorsDispatchTable:
    """Scenario: dispatch table routes known kinds and skips unknown kinds."""

    def test_table_has_exactly_known_content_kinds(self) -> None:
        assert set(_VALIDATORS) == {
            CONTENT_KIND_FEATURES,
            CONTENT_KIND_STATS,
            CONTENT_KIND_INSIGHT,
        }

    def test_features_kind_maps_to_features_validator(self) -> None:
        assert _VALIDATORS[CONTENT_KIND_FEATURES] is _validate_features_content

    def test_stats_kind_maps_to_stats_validator(self) -> None:
        assert _VALIDATORS[CONTENT_KIND_STATS] is _validate_stats_content

    def test_insight_kind_maps_to_insight_validator(self) -> None:
        assert _VALIDATORS[CONTENT_KIND_INSIGHT] is _validate_insight_content

    def test_unknown_content_kind_has_no_validator(self) -> None:
        # Scenario: unknown content_kind passes through (no validator registered).
        assert _VALIDATORS.get("bogus") is None

    def test_dispatched_features_validator_enforces_rules(self) -> None:
        validator = _VALIDATORS[CONTENT_KIND_FEATURES]
        with pytest.raises(ValueError, match=ERR_FEATURES_REQUIRED):
            validator({"features": None})
