"""Cross-slide body distinctness metrics for the editorial content phase (AE-0291).

Dependency-free token-Jaccard similarity used to detect near-duplicate slide
bodies so the generator can bounded-re-draft the offending slide once.
"""

from __future__ import annotations

import re

# A body is "too similar" to another when their token-Jaccard is at or above this.
DISTINCTNESS_SIMILARITY_THRESHOLD = 0.6
_MIN_TOKEN_LEN = 3
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(text.lower())
        if len(token) >= _MIN_TOKEN_LEN
    }


def body_similarity(left: str, right: str) -> float:
    """Token-Jaccard similarity of two slide bodies in [0.0, 1.0]."""
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection / union


def max_similarity_against(body: str, others: list[str]) -> float:
    """Highest similarity of ``body`` against every other body (0.0 if none)."""
    scores = [body_similarity(body, other) for other in others]
    return max(scores, default=0.0)


def find_duplicate_slide_indices(
    bodies: list[str],
    threshold: float = DISTINCTNESS_SIMILARITY_THRESHOLD,
) -> list[int]:
    """Indices whose body is >= threshold similar to an earlier (kept) body.

    The first occurrence is kept; each later near-duplicate is flagged for
    re-draft, so the result is deterministic and order-stable.
    """
    duplicates: list[int] = []
    for index in range(len(bodies)):
        for prior in range(index):
            if body_similarity(bodies[index], bodies[prior]) >= threshold:
                duplicates.append(index)
                break
    return duplicates


__all__ = [
    "DISTINCTNESS_SIMILARITY_THRESHOLD",
    "body_similarity",
    "find_duplicate_slide_indices",
    "max_similarity_against",
]
