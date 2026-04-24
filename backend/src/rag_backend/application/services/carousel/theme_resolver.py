"""Smart theme resolver for carousel projects.

Reproduces the creative palette-selection behavior of the original
carousel skill: brand-aware color detection, keyword-based category
fallback, and custom palette generation when a known brand is detected.
"""

from __future__ import annotations

from rag_backend.domain.constants import (
    BRAND_KEYWORDS,
    BRAND_PALETTES,
    CAROUSEL_THEMES,
    THEME_CATEGORY_KEYWORDS,
)
from rag_backend.domain.models import CarouselProject, CarouselTheme

DEFAULT_THEME_KEY = "ai_competition"


def _score_brands(text: str) -> dict[str, int]:
    """Count keyword matches for each brand in the given text.

    Returns a mapping of brand name -> match count. The text is
    lower-cased before matching so the keyword lists can stay in
    lower-case.
    """
    lowered = text.lower()
    scores: dict[str, int] = {}
    for brand, keywords in BRAND_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in lowered)
        if count:
            scores[brand] = count
    return scores


def _score_categories(text: str) -> dict[str, int]:
    """Count keyword matches for each theme category in the given text.

    Same logic as `_score_brands` but operates on the five predefined
    category keyword lists.
    """
    lowered = text.lower()
    scores: dict[str, int] = {}
    for theme, keywords in THEME_CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in lowered)
        if count:
            scores[theme] = count
    return scores


def _detect_brand(text: str) -> str | None:
    """Return the brand with the highest keyword score, or None."""
    scores = _score_brands(text)
    if not scores:
        return None
    return max(scores, key=scores.get)  # type: ignore[arg-type]


def _detect_category(text: str) -> str:
    """Return the category theme key with the highest keyword score.

    Falls back to ``DEFAULT_THEME_KEY`` when no keywords match.
    """
    scores = _score_categories(text)
    if not scores:
        return DEFAULT_THEME_KEY
    return max(scores, key=scores.get)  # type: ignore[arg-type]


def resolve_theme(project: CarouselProject) -> dict[str, str]:
    """Pick the color theme for this project.

    Resolution order:
    1. If the user picked an explicit theme (not AUTO), return it.
    2. Build a single text blob from ``topic``, ``title``, ``subtitle``,
       and ``niche``.
    3. Run brand detection on that blob. If a brand is detected with at
       least one keyword match, return the brand's custom palette.
    4. Run category detection on the same blob. Return the best-matching
       predefined theme.
    5. If nothing matches, fall back to ``DEFAULT_THEME_KEY``.

    The returned dict always has ``primary``, ``accent``, and
    ``background`` keys.
    """
    if project.theme != CarouselTheme.AUTO:
        return CAROUSEL_THEMES.get(
            project.theme.value,
            CAROUSEL_THEMES[DEFAULT_THEME_KEY],
        )

    text_parts = [
        project.topic or "",
        project.title or "",
        project.subtitle or "",
        project.niche or "",
    ]
    analysis_text = " ".join(text_parts)

    brand = _detect_brand(analysis_text)
    if brand is not None:
        return BRAND_PALETTES.get(brand, CAROUSEL_THEMES[DEFAULT_THEME_KEY])

    category = _detect_category(analysis_text)
    return CAROUSEL_THEMES.get(category, CAROUSEL_THEMES[DEFAULT_THEME_KEY])
