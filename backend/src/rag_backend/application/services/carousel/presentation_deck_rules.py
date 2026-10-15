"""Deck-level presentation rules for contracts with roles (AE-0374, ADR-0021).

Per-slide validation cannot see the deck. These rules run once per deck and
only for role contracts (``pov_hook_v1``, ``hero_lower_third_v4``), so the
fixed v1-v3 decks keep exactly their previous reports.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_SLIDE_COUNT_INVALID,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation

MSG_SLIDE_COUNT_INVALID = (
    "The deck has {count} slides; the contract accepts {low}-{high}"
)


def slide_count_violations(
    slide_total: int, policy: CarouselPresentationPolicy
) -> list[SlideValidationViolation]:
    """``slide_count_invalid`` when a role deck's size is outside the range."""
    span = policy.slide_range
    if not policy.has_roles or span.accepts(slide_total):
        return []
    return [
        SlideValidationViolation(
            code=VIOLATION_SLIDE_COUNT_INVALID,
            message=MSG_SLIDE_COUNT_INVALID.format(
                count=slide_total, low=span.minimum, high=span.maximum
            ),
            severity=policy.severity_for(VIOLATION_SLIDE_COUNT_INVALID),
        )
    ]


def deck_violations(
    localized_slides: list[dict[str, object]], policy: CarouselPresentationPolicy
) -> list[SlideValidationViolation]:
    """Every deck-level violation for ``localized_slides``."""
    return slide_count_violations(len(localized_slides), policy)


__all__ = ["deck_violations", "slide_count_violations"]
