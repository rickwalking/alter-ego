"""Cosine similarity shared by the quality, feedback and plagiarism checks.

Scenario: identical vectors score 1.
Scenario: orthogonal vectors score 0.
Scenario: a zero vector scores 0.
Scenario: mismatched lengths raise.
"""

from __future__ import annotations

import pytest

from rag_backend.domain.similarity import cosine_similarity


# Scenario: identical vectors score 1.
def test_identical_vectors_score_one() -> None:
    assert cosine_similarity([3.0, 4.0], [3.0, 4.0]) == pytest.approx(1.0)


# Scenario: orthogonal vectors score 0.
def test_orthogonal_vectors_score_zero() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


# Scenario: a zero vector scores 0.
@pytest.mark.parametrize(
    ("a", "b"), [([0.0, 0.0], [1.0, 0.0]), ([1.0, 0.0], [0.0, 0.0])]
)
def test_zero_vector_scores_zero(a: list[float], b: list[float]) -> None:
    assert cosine_similarity(a, b) == 0.0


# Scenario: mismatched lengths raise.
def test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="argument"):
        cosine_similarity([1.0, 0.0], [1.0])
