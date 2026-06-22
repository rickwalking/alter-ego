"""Smart theme resolver for carousel projects.

Reproduces the creative palette-selection behavior of the original
carousel skill: brand-aware color detection, keyword-based category
fallback, and diverse palette selection when auto-detecting themes.
"""

from __future__ import annotations

import hashlib

from rag_backend.domain.constants import (
    AUTO_ROTATION_THEME_KEYS,
    BRAND_KEYWORDS,
    BRAND_PALETTES,
    CAROUSEL_THEMES,
    ENCODING_UTF8,
    THEME_CATEGORY_KEYWORDS,
)
from rag_backend.domain.models import CarouselProject, CarouselTheme

# Rotation pool used when no brand or category keyword matches. Limited to the
# original dark category themes (``AUTO_ROTATION_THEME_KEYS``) so AUTO never
# hands a LIGHT palette to a dark image strategy. Explicit-select palettes
# (new dark variants + light/editorial) are reachable only via an explicit
# ``project.theme``.
CATEGORY_THEME_KEYS: tuple[str, ...] = AUTO_ROTATION_THEME_KEYS


def _hash_to_theme_key(text: str) -> str:
    """Deterministically map *text* to one of the category theme keys.

    Uses a stable hash so the same topic always yields the same theme,
    while different topics spread evenly across the available palettes.
    This prevents the repetitive fallback where every unmatched topic
    received the same default colors.
    """
    digest = hashlib.sha256(text.encode(ENCODING_UTF8)).hexdigest()
    index = int(digest, 16) % len(CATEGORY_THEME_KEYS)
    return CATEGORY_THEME_KEYS[index]


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


def _detect_category(text: str) -> str | None:
    """Return the category theme key with the highest keyword score.

    Returns ``None`` when no keywords match, letting the caller pick a
    diverse fallback instead of a static default.
    """
    scores = _score_categories(text)
    if not scores:
        return None
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
    5. If nothing matches, deterministically rotate through all
       available category themes based on a hash of the topic text.
       This guarantees creative diversity without randomness.

    The returned dict always has ``primary``, ``accent``, and
    ``background`` keys.
    """
    if project.theme != CarouselTheme.AUTO:
        return CAROUSEL_THEMES.get(
            project.theme.value,
            CAROUSEL_THEMES[CATEGORY_THEME_KEYS[0]],
        )

    text_parts = [
        project.topic or "",
        project.title or "",
        project.niche or "",
    ]
    analysis_text = " ".join(text_parts)

    brand = _detect_brand(analysis_text)
    if brand is not None:
        return BRAND_PALETTES.get(
            brand, CAROUSEL_THEMES[_hash_to_theme_key(analysis_text)]
        )

    category = _detect_category(analysis_text)
    if category is not None:
        return CAROUSEL_THEMES.get(
            category, CAROUSEL_THEMES[_hash_to_theme_key(analysis_text)]
        )

    return CAROUSEL_THEMES[_hash_to_theme_key(analysis_text)]
