"""Deck-level presentation rules for contracts with roles (AE-0374, AE-0375).

Per-slide validation cannot see the deck. These rules run once per deck and
only for role contracts (``pov_hook_v1``, ``hero_lower_third_v4``), so the
fixed v1-v3 decks keep exactly their previous reports. A role rule (hook word
limit, first person) fires only when the contract declares its severity.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.pov_checks import (
    MIN_FIRST_PERSON_SLIDES,
    first_person_slide_count,
    hook_too_long,
)
from rag_backend.application.services.carousel.presentation_policy_range import (
    expand_policy_for_count,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_SLIDE_COUNT_INVALID,
)
from rag_backend.domain.constants.presentation_roles import (
    ROLE_HOOK,
    VIOLATION_FIRST_PERSON_MISSING,
    VIOLATION_HOOK_WORD_LIMIT,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation

MSG_SLIDE_COUNT_INVALID = (
    "The deck has {count} slides; the contract accepts {low}-{high}"
)
MSG_HOOK_WORD_LIMIT = "The slide 1 hook has {count} words; the limit is 10"
MSG_FIRST_PERSON_MISSING = (
    "Only {count} slides speak in the first person; write at least {minimum}"
)
_KEY_HEADING = "heading"
_KEY_BODY = "body"


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


def _pt_copy(slide: dict[str, object]) -> tuple[str, str]:
    copy = as_dict(slide.get(PRESENTATION_PT_KEY)) or {}
    return str(copy.get(_KEY_HEADING) or ""), str(copy.get(_KEY_BODY) or "")


def _declares(policy: CarouselPresentationPolicy, code: str) -> bool:
    return code in policy.rule_severities


def _hook_violations(
    slides: list[dict[str, object]], policy: CarouselPresentationPolicy
) -> list[SlideValidationViolation]:
    violations: list[SlideValidationViolation] = []
    for slide_policy, slide in zip(policy.slides, slides, strict=False):
        heading, _body = _pt_copy(slide)
        if slide_policy.role != ROLE_HOOK or not hook_too_long(heading):
            continue
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_HOOK_WORD_LIMIT,
                message=MSG_HOOK_WORD_LIMIT.format(count=len(heading.split())),
                slide_index=slide_policy.slide_number,
                locale=LANGUAGE_PT,
                field=_KEY_HEADING,
                severity=policy.severity_for(VIOLATION_HOOK_WORD_LIMIT),
            )
        )
    return violations


def _first_person_violations(
    slides: list[dict[str, object]], policy: CarouselPresentationPolicy
) -> list[SlideValidationViolation]:
    texts = [" ".join(_pt_copy(slide)) for slide in slides]
    count = first_person_slide_count(texts)
    if count >= MIN_FIRST_PERSON_SLIDES:
        return []
    return [
        SlideValidationViolation(
            code=VIOLATION_FIRST_PERSON_MISSING,
            message=MSG_FIRST_PERSON_MISSING.format(
                count=count, minimum=MIN_FIRST_PERSON_SLIDES
            ),
            locale=LANGUAGE_PT,
            severity=policy.severity_for(VIOLATION_FIRST_PERSON_MISSING),
        )
    ]


def role_violations(
    slides: list[dict[str, object]], policy: CarouselPresentationPolicy
) -> list[SlideValidationViolation]:
    """The POV rubric rules the contract declares, on a deck of a valid size."""
    if not policy.has_roles or not policy.slide_range.accepts(len(slides)):
        return []
    sized = expand_policy_for_count(policy, len(slides))
    violations: list[SlideValidationViolation] = []
    if _declares(sized, VIOLATION_HOOK_WORD_LIMIT):
        violations.extend(_hook_violations(slides, sized))
    if _declares(sized, VIOLATION_FIRST_PERSON_MISSING):
        violations.extend(_first_person_violations(slides, sized))
    return violations


def deck_violations(
    localized_slides: list[dict[str, object]], policy: CarouselPresentationPolicy
) -> list[SlideValidationViolation]:
    """Every deck-level violation for ``localized_slides``."""
    return [
        *slide_count_violations(len(localized_slides), policy),
        *role_violations(localized_slides, policy),
    ]


__all__ = ["deck_violations", "role_violations", "slide_count_violations"]
