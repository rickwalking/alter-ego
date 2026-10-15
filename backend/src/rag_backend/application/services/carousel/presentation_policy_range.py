"""Slide-count ranges and roles in presentation contracts (AE-0374, ADR-0021).

A contract without ``slide_count_min``/``slide_count_max`` keeps its fixed
``slide_count`` exactly as before. A ranged contract lists its LONGEST
sequence (``slide_count`` = max) and marks the droppable slides ``optional``;
``expand_policy_for_count`` drops the last optional slides and renumbers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
    PresentationPolicyError,
    SlideCountRange,
    SlideTypePolicy,
)
from rag_backend.domain.constants.presentation_policy import (
    ERR_PRESENTATION_POLICY_INVALID,
)
from rag_backend.domain.constants.presentation_roles import (
    KNOWN_ROLES,
    ROLE_SLIDE_TYPES,
)

KEY_SLIDE_COUNT_MIN = "slide_count_min"
KEY_SLIDE_COUNT_MAX = "slide_count_max"
KEY_SLIDE_COUNT_DEFAULT = "slide_count_default"
ERR_SLIDE_COUNT_OUT_OF_RANGE = "slide_count_out_of_range"


def _int_or_none(document: Mapping[str, object], key: str) -> int | None:
    value = document.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return value


def validate_roles(slides: tuple[SlideTypePolicy, ...]) -> None:
    """All slides have a known role matching their type, or none has a role."""
    with_role = [slide for slide in slides if slide.role]
    if not with_role:
        return
    if len(with_role) != len(slides):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    for slide in with_role:
        role = slide.role or ""
        if role not in KNOWN_ROLES or slide.slide_type not in ROLE_SLIDE_TYPES[role]:
            raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)


def parse_slide_range(
    document: Mapping[str, object],
    slides: tuple[SlideTypePolicy, ...],
) -> SlideCountRange | None:
    """The contract's deck-size range, or None for a fixed contract."""
    minimum = _int_or_none(document, KEY_SLIDE_COUNT_MIN)
    maximum = _int_or_none(document, KEY_SLIDE_COUNT_MAX)
    optional = sum(1 for slide in slides if slide.optional)
    if minimum is None and maximum is None:
        if optional:
            raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
        return None
    if minimum is None or maximum is None:
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    default = _int_or_none(document, KEY_SLIDE_COUNT_DEFAULT) or minimum
    span = SlideCountRange(minimum=minimum, maximum=maximum, default=default)
    _check_range(span, len(slides), optional)
    return span


def _check_range(span: SlideCountRange, longest: int, optional: int) -> None:
    valid = (
        1 <= span.minimum <= span.maximum
        and span.accepts(span.default)
        and span.maximum == longest
        and optional == span.maximum - span.minimum
    )
    if not valid:
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)


def _kept_slides(
    slides: tuple[SlideTypePolicy, ...], drop: int
) -> tuple[SlideTypePolicy, ...]:
    """Drop the last ``drop`` optional slides, then renumber from 1."""
    optional_numbers = [slide.slide_number for slide in slides if slide.optional]
    dropped = set(optional_numbers[len(optional_numbers) - drop :]) if drop else set()
    kept = [slide for slide in slides if slide.slide_number not in dropped]
    return tuple(
        replace(slide, slide_number=number) for number, slide in enumerate(kept, 1)
    )


def expand_policy_for_count(
    policy: CarouselPresentationPolicy, count: int
) -> CarouselPresentationPolicy:
    """The policy sized to ``count`` slides (8 POV slides keep 2 points, etc.)."""
    if not policy.slide_range.accepts(count):
        raise PresentationPolicyError(ERR_SLIDE_COUNT_OUT_OF_RANGE)
    if count == len(policy.slides):
        return policy
    slides = _kept_slides(policy.slides, len(policy.slides) - count)
    return replace(
        policy,
        slide_count=count,
        slides=slides,
        artwork_slides=tuple(s.slide_number for s in slides if s.image_required),
    )


__all__ = [
    "ERR_SLIDE_COUNT_OUT_OF_RANGE",
    "KEY_SLIDE_COUNT_DEFAULT",
    "KEY_SLIDE_COUNT_MAX",
    "KEY_SLIDE_COUNT_MIN",
    "expand_policy_for_count",
    "parse_slide_range",
    "validate_roles",
]
