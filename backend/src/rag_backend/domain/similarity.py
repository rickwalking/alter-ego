"""Vector similarity shared by the quality, feedback and plagiarism checks."""

from __future__ import annotations


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine of the angle between ``a`` and ``b``; ``0.0`` when either is all zeros."""
    dot_product = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))
