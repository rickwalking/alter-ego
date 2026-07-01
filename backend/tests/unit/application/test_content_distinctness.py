"""Unit tests for cross-slide content distinctness metrics (AE-0291)."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.content_distinctness import (
    DISTINCTNESS_SIMILARITY_THRESHOLD,
    body_similarity,
    find_duplicate_slide_indices,
    max_similarity_against,
)


@pytest.mark.unit
class TestBodySimilarity:
    def test_identical_bodies_score_one(self) -> None:
        text = "open weight models reach parity with closed frontier models"
        assert body_similarity(text, text) == pytest.approx(1.0)

    def test_disjoint_bodies_score_zero(self) -> None:
        assert body_similarity(
            "alpha bravo charlie delta", "sierra tango uniform victor"
        ) == pytest.approx(0.0)

    def test_empty_body_scores_zero(self) -> None:
        assert body_similarity("", "anything here") == pytest.approx(0.0)

    def test_partial_overlap_between_zero_and_one(self) -> None:
        score = body_similarity(
            "citizen access to frontier models is unfeasible today",
            "citizen access remains limited for frontier compute today",
        )
        assert 0.0 < score < 1.0


@pytest.mark.unit
class TestDuplicateDetection:
    def test_flags_later_near_duplicate_keeps_first(self) -> None:
        bodies = [
            "vulnerability discovery is a national security risk for nations",
            "vulnerability discovery is a national security risk for nations today",
            "open weight parity changes the competitive landscape entirely",
        ]
        assert find_duplicate_slide_indices(bodies) == [1]

    def test_distinct_bodies_have_no_duplicates(self) -> None:
        bodies = [
            "alpha topic about compute scaling laws",
            "bravo topic about governance and policy",
            "charlie topic about open weight ecosystems",
        ]
        assert find_duplicate_slide_indices(bodies) == []

    def test_threshold_constant_is_a_ratio(self) -> None:
        assert 0.0 < DISTINCTNESS_SIMILARITY_THRESHOLD <= 1.0

    def test_max_similarity_against_excludes_none(self) -> None:
        assert max_similarity_against("solo body text", []) == pytest.approx(0.0)
