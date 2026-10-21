"""Per-post image budget (``BLOG_IMAGE_COST_CAP``, ADR-0025).

Every generated image (cover or section, first try or regenerate) counts
against the post's budget in ``ai_generation_metadata``; generation is refused
before any provider spend once the cap is reached. Bulk generation
counts through the same helpers.
"""

from __future__ import annotations

from rag_backend.domain.constants.blog_editor import BLOG_IMAGE_GENERATIONS_KEY


def image_generations(metadata: object) -> int:
    """How many images were generated for this post so far."""
    if not isinstance(metadata, dict):
        return 0
    value = metadata.get(BLOG_IMAGE_GENERATIONS_KEY, 0)
    return value if isinstance(value, int) and value > 0 else 0


def within_budget(metadata: object, cap: int) -> bool:
    """``True`` while another image may be generated."""
    return image_generations(metadata) < cap


def count_one_image(metadata: dict[str, object]) -> dict[str, object]:
    """``metadata`` with one more generated image counted."""
    return {**metadata, BLOG_IMAGE_GENERATIONS_KEY: image_generations(metadata) + 1}


__all__ = ["count_one_image", "image_generations", "within_budget"]
