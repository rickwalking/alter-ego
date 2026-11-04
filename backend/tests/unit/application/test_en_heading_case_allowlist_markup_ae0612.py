"""The EN heading-case allowlist applies to the first visible word.

Feature: tests/features/en_heading_case_allowlist_inside_markup_ae0612.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.nodes.export import (
    BilingualExportConfig,
    run_bilingual_export,
)
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
from rag_backend.application.services.carousel.sentence_case import (
    opens_with_allowlisted,
)
from rag_backend.application.services.carousel.types import (
    SlideData,
    slides_data_for_language,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation

pytestmark = pytest.mark.unit

_EXPORT = "rag_backend.application.services.carousel.nodes.export"
_ALLOWLIST = ("iPhone", "eBay", "macOS")
_WRAPPED_TOKEN = "<strong>iPhone</strong> tips"
_WRAPPED_LOWER = "<strong>word</strong> that matters"
_WRAPPED_FIXED = "<strong>Word</strong> that matters"


@pytest.fixture
def policy() -> CarouselPresentationPolicy:
    return load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1)


@pytest.fixture
def casing_policy() -> CarouselPresentationPolicy:
    return load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4)


def _violations(
    payload: dict[str, object], policy: CarouselPresentationPolicy
) -> tuple[SlideValidationViolation, ...]:
    return tuple(
        validate_slide_payload(
            ValidatePayloadCommand(payload, locale=LANGUAGE_EN, policy=policy)
        )
    )


def _fires(heading: str, policy: CarouselPresentationPolicy) -> bool:
    payload: dict[str, object] = {
        "slide_type": "content",
        "heading": heading,
        "body": "Detail.",
    }
    codes = {violation.code for violation in _violations(payload, policy)}
    return VIOLATION_HEADING_NOT_SENTENCE_CASE_EN in codes


def _with_lowercase_item_title(heading: str) -> dict[str, object]:
    return {
        "slide_type": "content",
        "heading": heading,
        "body": "Detail.",
        "features": [{"title": "lowercase title", "body": "Detail."}],
    }


@pytest.mark.parametrize(
    "heading",
    [
        # Scenario: An allowlisted token wrapped in a strong tag passes
        _WRAPPED_TOKEN,
        # Scenario: An allowlisted token under nested tags passes
        "<strong><em>eBay</em></strong> tips",
        # Scenario: A plain heading that opens with an allowlisted token passes
        "iPhone tips",
        # Scenario: A heading that is only an allowlisted token still passes
        "macOS",
    ],
)
def test_opening_allowlisted_token_does_not_fire(
    heading: str, policy: CarouselPresentationPolicy
) -> None:
    assert not _fires(heading, policy)


@pytest.mark.parametrize(
    "heading",
    [
        # Scenario: A plain lowercase heading still fires
        "word that matters",
        # Scenario: A lowercase word wrapped in a strong tag still fires
        _WRAPPED_LOWER,
        # Scenario: The allowlist match stays case-sensitive
        "iphone tips",
        "<strong>iphone</strong> tips",
        # Scenario: A token that is only the prefix of a longer word still fires
        "iPhoneX tips",
        # Scenario: A token that is only the prefix of a wrapped longer word still fires
        "<strong>eBayer</strong> tips",
        # Scenario: A token after the first visible word is not an opening token
        "5 iPhone tips",
    ],
)
def test_rule_still_fires_on_a_seeded_lowercase_heading(
    heading: str, policy: CarouselPresentationPolicy
) -> None:
    assert _fires(heading, policy)


def test_rule_uses_the_contract_allowlist_unchanged(
    policy: CarouselPresentationPolicy,
) -> None:
    assert policy.intentional_lowercase_allowlist == _ALLOWLIST


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Scenario: A plain heading that opens with an allowlisted token passes
        ("iPhone tips", True),
        # Scenario: A heading that is only an allowlisted token still passes
        ("macOS", True),
        # Scenario: An allowlisted token under nested tags passes
        ("  <b><i>eBay</i></b>", True),
        # Scenario: A token that is only the prefix of a longer word still fires
        ("iPhoneX", False),
        # Scenario: A token after the first visible word is not an opening token
        ("the iPhone", False),
        # Scenario: The allowlist match stays case-sensitive
        ("iphone", False),
        # Scenario: A heading that has no visible text has no opening token
        ("<strong></strong>", False),
        ("", False),
    ],
)
def test_opens_with_allowlisted(text: str, expected: bool) -> None:
    assert opens_with_allowlisted(text, _ALLOWLIST) is expected


def test_repair_keeps_allowlisted_heading_next_to_lowercase_item_title(
    casing_policy: CarouselPresentationPolicy,
) -> None:
    # Scenario: The repair leaves a wrapped allowlisted heading as it is
    payload = _with_lowercase_item_title(_WRAPPED_TOKEN)
    violations = _violations(payload, casing_policy)
    heading_code_fields = [
        violation.field
        for violation in violations
        if violation.code == VIOLATION_HEADING_NOT_SENTENCE_CASE_EN
    ]
    assert heading_code_fields == ["features[0].title"]

    repaired = deterministic_repair_slide_payload(payload, violations, LANGUAGE_EN)

    assert repaired["heading"] == _WRAPPED_TOKEN


def test_repair_fixes_lowercase_heading_next_to_lowercase_item_title(
    casing_policy: CarouselPresentationPolicy,
) -> None:
    # Scenario: The repair still fixes a lowercase heading next to a lowercase item title
    payload = _with_lowercase_item_title(_WRAPPED_LOWER)
    violations = _violations(payload, casing_policy)

    repaired = deterministic_repair_slide_payload(payload, violations, LANGUAGE_EN)

    assert repaired["heading"] == _WRAPPED_FIXED


def test_repair_still_runs_on_a_violation_without_a_field() -> None:
    # Scenario: The repair still fixes a lowercase heading next to a lowercase item title
    violation = SlideValidationViolation(
        code=VIOLATION_HEADING_NOT_SENTENCE_CASE_EN, message="lowercase"
    )
    payload: dict[str, object] = {"heading": _WRAPPED_LOWER}

    repaired = deterministic_repair_slide_payload(payload, (violation,), LANGUAGE_EN)

    assert repaired["heading"] == _WRAPPED_FIXED


def _en_slide(heading: str, body: str) -> SlideData:
    translation: dict[str, object] = {"heading": heading, "body": body}
    return SlideData(1, "content", "PT", "PT", translation_en=translation)


def test_en_export_keeps_allowlisted_token() -> None:
    # Scenario: The EN export keeps an allowlisted token in the heading and the body
    body = "iPhone owners win."
    slide = _en_slide(_WRAPPED_TOKEN, body)

    [en] = slides_data_for_language([slide], LANGUAGE_EN, _ALLOWLIST)

    assert (en.heading, en.body) == (_WRAPPED_TOKEN, body)


def test_en_export_still_sentence_cases_other_copy() -> None:
    # Scenario: The EN export still sentence-cases other lowercase copy
    slide = _en_slide(_WRAPPED_LOWER, "detail here.")

    [en] = slides_data_for_language([slide], LANGUAGE_EN, _ALLOWLIST)

    assert (en.heading, en.body) == (_WRAPPED_FIXED, "Detail here.")


@pytest.mark.parametrize(
    "policy_version", [None, PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4]
)
async def test_bilingual_export_uses_the_project_policy_allowlist(
    policy_version: str | None, tmp_path: Path
) -> None:
    # Scenario: The EN export keeps an allowlisted token in the heading and the body
    config = BilingualExportConfig(
        project=CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            presentation_policy_version=policy_version,
        ),
        slides_data=[_en_slide(_WRAPPED_TOKEN, "Detail.")],
        pt_html="<html></html>",
        output_dir=tmp_path,
        export=MagicMock(),
        pdf_builder=MagicMock(),
    )

    with (
        patch(f"{_EXPORT}.render_language", new=AsyncMock()),
        patch(f"{_EXPORT}.run_design", return_value="<html></html>") as design,
    ):
        await run_bilingual_export(config)

    [en] = design.call_args.args[1]
    assert en.heading == _WRAPPED_TOKEN
