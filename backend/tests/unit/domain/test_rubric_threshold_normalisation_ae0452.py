"""Stored rubric thresholds read as fractions of their own scale.

Feature: rubric_evaluation_ae0452.feature
"""

from __future__ import annotations

import pytest

from rag_backend.domain.models.rubric import ScoringScale
from rag_backend.domain.rubric_scoring import (
    normalize_stored_criterion,
    normalize_threshold,
)


# Scenario: A legacy threshold on a 1-10 criterion is read on its own scale
@pytest.mark.parametrize(
    ("stored", "scale", "fraction"),
    [
        (7.0, ScoringScale.SCORE_1_10, 0.7),
        (10.0, ScoringScale.SCORE_1_10, 1.0),
        (70.0, ScoringScale.SCORE_0_100, 0.7),
        (100.0, ScoringScale.SCORE_0_100, 1.0),
        (70.0, ScoringScale.PASS_FAIL, 0.7),
        (0.7, ScoringScale.SCORE_1_10, 0.7),
        (1.0, ScoringScale.SCORE_0_100, 1.0),
    ],
)
def test_legacy_threshold_reads_on_its_scale(
    stored: float, scale: ScoringScale, fraction: float
) -> None:
    assert normalize_threshold(stored, scale) == pytest.approx(fraction)


# Scenario: A legacy threshold above the scale maximum is read as a percentage
@pytest.mark.parametrize(
    ("stored", "scale", "fraction"),
    [
        (70.0, ScoringScale.SCORE_1_10, 0.7),
        (11.0, ScoringScale.SCORE_1_10, 0.11),
        (150.0, ScoringScale.SCORE_0_100, 1.0),
        (150.0, ScoringScale.SCORE_1_10, 1.0),
    ],
)
def test_threshold_above_the_scale_reads_as_a_percentage(
    stored: float, scale: ScoringScale, fraction: float
) -> None:
    assert normalize_threshold(stored, scale) == pytest.approx(fraction)


# Scenario: A legacy threshold on a 1-10 criterion is read on its own scale
def test_stored_criterion_is_normalised_and_other_fields_kept() -> None:
    stored = {"id": "c", "min_threshold": 7, "scoring_scale": "1-10"}

    assert normalize_stored_criterion(stored) == {
        "id": "c",
        "min_threshold": pytest.approx(0.7),
        "scoring_scale": "1-10",
    }
    assert stored["min_threshold"] == 7


# Scenario: A legacy percentage threshold is read as a fraction
@pytest.mark.parametrize("threshold", [True, "70", None])
def test_non_numeric_threshold_is_left_for_validation(threshold: object) -> None:
    stored = {"min_threshold": threshold, "scoring_scale": "0-100"}

    assert normalize_stored_criterion(stored) == stored
