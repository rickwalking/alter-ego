"""The EN heading-case check reads the first visible letter.

Feature: tests/features/en_heading_case_leading_markup_ae0605.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_copy_repair import (
    deterministic_repair_slide_payload,
)
from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_validation import (
    ValidatePayloadCommand,
    validate_slide_payload,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation

pytestmark = pytest.mark.unit

_WRAPPED_UPPER = "<strong>Word</strong> that matters"
_WRAPPED_LOWER = "<strong>word</strong> that matters"


@pytest.fixture
def policy() -> CarouselPresentationPolicy:
    return load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1)


def _violations(
    heading: str,
    policy: CarouselPresentationPolicy,
    locale: str = LANGUAGE_EN,
) -> list[SlideValidationViolation]:
    payload = {"slide_type": "content", "heading": heading, "body": "Detail."}
    return validate_slide_payload(
        ValidatePayloadCommand(payload, locale=locale, policy=policy)
    )


def _fires(heading: str, policy: CarouselPresentationPolicy) -> bool:
    codes = {violation.code for violation in _violations(heading, policy)}
    return VIOLATION_HEADING_NOT_SENTENCE_CASE_EN in codes


@pytest.mark.parametrize(
    "heading",
    [
        # Scenario: A heading that starts with a strong tag and an uppercase letter passes
        _WRAPPED_UPPER,
        # Scenario: Nested tags before an uppercase letter pass
        "<strong><em>Word</em></strong> that matters",
        # Scenario: A closing tag and whitespace before an uppercase letter pass
        "  </em> <strong>Word</strong> that matters",
        # Scenario: A heading that is only markup has no letter to check
        "<strong></strong>",
    ],
)
def test_visible_uppercase_or_no_letter_does_not_fire(
    heading: str, policy: CarouselPresentationPolicy
) -> None:
    assert not _fires(heading, policy)


@pytest.mark.parametrize(
    "heading",
    [
        # Scenario: A plain lowercase heading still fires
        "word that matters",
        # Scenario: A lowercase heading wrapped in a strong tag still fires
        _WRAPPED_LOWER,
        # Scenario: A lowercase heading under nested tags still fires
        "<strong><em>word</em></strong> that matters",
    ],
)
def test_visible_lowercase_fires(
    heading: str, policy: CarouselPresentationPolicy
) -> None:
    assert _fires(heading, policy)


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        # Scenario: A non-letter first character keeps its current result
        ("5 tips that matter", True),
        ("5 Tips that matter", False),
        ('"word" that matters', True),
        ('"Word" that matters', False),
        ("5 <strong>tips</strong> that matter", True),
        ("5 <strong>Tips</strong> that matter", False),
        ("100", False),
    ],
)
def test_non_letter_first_character_defers_to_the_next_letter(
    heading: str, expected: bool, policy: CarouselPresentationPolicy
) -> None:
    assert _fires(heading, policy) is expected


def test_the_rule_stays_en_only(policy: CarouselPresentationPolicy) -> None:
    # Scenario: The rule stays EN-only
    violations = _violations(
        "<strong>palavra</strong> que importa", policy, LANGUAGE_PT
    )
    codes = {violation.code for violation in violations}
    assert VIOLATION_HEADING_NOT_SENTENCE_CASE_EN not in codes


def test_repair_capitalizes_the_visible_letter_and_keeps_the_tag(
    policy: CarouselPresentationPolicy,
) -> None:
    # Scenario: The repair capitalizes the visible letter and keeps the tag
    payload = {"slide_type": "content", "heading": _WRAPPED_LOWER, "body": "Detail."}
    violations = tuple(_violations(_WRAPPED_LOWER, policy))
    repaired = deterministic_repair_slide_payload(payload, violations, LANGUAGE_EN)
    assert repaired["heading"] == _WRAPPED_UPPER
    assert not _fires(_WRAPPED_UPPER, policy)


def test_correct_wrapped_heading_is_left_as_it_is(
    policy: CarouselPresentationPolicy,
) -> None:
    # Scenario: An already correct wrapped heading is left as it is
    payload = {"slide_type": "content", "heading": _WRAPPED_UPPER, "body": "Detail."}
    violations = tuple(_violations(_WRAPPED_UPPER, policy))
    repaired = deterministic_repair_slide_payload(payload, violations, LANGUAGE_EN)
    assert repaired["heading"] == _WRAPPED_UPPER
