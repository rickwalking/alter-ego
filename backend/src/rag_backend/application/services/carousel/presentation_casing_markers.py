"""Deterministic sentence-case repair that still triggers regeneration.

Prod carousel 8e350d6e: the bounded repair silently capitalized the stored
localized copy, so the report said ``valid`` while proper nouns stayed
lowercase ("argon", "brasil") and the rendered slides kept the raw copy.

The content build now repairs sentence case BEFORE validation (first letter
only, locale-safe, allowlist-aware; proper nouns are never guessed) and records
a slide-level marker for every field it had to fix. The markers are folded into
validation as BLOCKING violations of the matching sentence-case rule on every
read path, so the content goes back for regeneration (fail-closed retry, then
the review gate / autopilot revise) instead of passing on a cosmetic fix. A
reviewer edit of a locale drops that locale's markers.

The repair message states the problem and the fix only; it never claims the text was
auto-capitalized, since only sentence starts are touched and proper nouns are never
guessed.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.presentation_casing import (
    repair_casing,
    sentence_case_findings,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.workflow_state_fields import STATE_FIELD_SLIDE_INDEX
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationViolation,
    ViolationSeverity,
)

CASING_REPAIRS_KEY = "casing_repairs"
CASING_MARKER_LOCALE = "locale"
CASING_MARKER_FIELD = "field"
CASING_MARKER_CODE = "code"
CASING_REPAIR_MESSAGE = (
    "The model wrote this text in lowercase. Edit or regenerate this slide: "
    "start every sentence with a capital letter and capitalize proper nouns"
)

_LOCALE_PAYLOADS: tuple[tuple[str, str], ...] = (
    (PRESENTATION_PT_KEY, LANGUAGE_PT),
    (PRESENTATION_EN_KEY, LANGUAGE_EN),
)


def _markers(slide: Mapping[str, object]) -> list[dict[str, object]]:
    raw = slide.get(CASING_REPAIRS_KEY)
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _repair_slide(
    slide: Mapping[str, object],
    policy: CarouselPresentationPolicy,
) -> dict[str, object]:
    updated = dict(slide)
    markers = _markers(updated)
    for payload_key, locale in _LOCALE_PAYLOADS:
        payload = as_dict(updated.get(payload_key))
        if payload is None:
            continue
        findings = sentence_case_findings(payload, locale, policy)
        if not findings:
            continue
        updated[payload_key] = repair_casing(payload, locale, policy)
        markers.extend(
            {
                CASING_MARKER_LOCALE: locale,
                CASING_MARKER_FIELD: finding.field,
                CASING_MARKER_CODE: finding.code,
            }
            for finding in findings
        )
    if markers:
        updated[CASING_REPAIRS_KEY] = markers
    return updated


def apply_sentence_case_repair(
    localized_slides: list[dict[str, object]],
    policy: CarouselPresentationPolicy,
) -> list[dict[str, object]]:
    """Capitalize lowercase sentence starts and mark every repaired field.

    Active only for policies that enforce the quality rubric (v3+); earlier
    versions keep their frozen semantics (the bounded repair alone).
    """
    if not policy.enforces_quality_rubric:
        return [dict(slide) for slide in localized_slides]
    return [_repair_slide(slide, policy) for slide in localized_slides]


def _severity(policy: CarouselPresentationPolicy, code: str) -> ViolationSeverity:
    return "warning" if policy.is_casing_warning(code) else "blocker"


def casing_marker_violations(
    slide: Mapping[str, object],
    policy: CarouselPresentationPolicy,
) -> list[SlideValidationViolation]:
    """Derive the (blocking) violations recorded by the sentence-case repair."""
    slide_index_value = slide.get(STATE_FIELD_SLIDE_INDEX)
    slide_index = slide_index_value if isinstance(slide_index_value, int) else None
    violations: list[SlideValidationViolation] = []
    for marker in _markers(slide):
        code = marker.get(CASING_MARKER_CODE)
        if not isinstance(code, str) or code not in policy.rule_severities:
            continue
        locale = marker.get(CASING_MARKER_LOCALE)
        field = marker.get(CASING_MARKER_FIELD)
        violations.append(
            SlideValidationViolation(
                code=code,
                message=CASING_REPAIR_MESSAGE,
                slide_index=slide_index,
                locale=locale if isinstance(locale, str) else None,
                field=field if isinstance(field, str) else None,
                severity=_severity(policy, code),
            )
        )
    return violations


def drop_casing_repair_markers(slide: dict[str, object], locale: str) -> None:
    """Remove a locale's casing markers (a reviewer edit supersedes them)."""
    kept = [
        marker
        for marker in _markers(slide)
        if marker.get(CASING_MARKER_LOCALE) != locale
    ]
    if kept:
        slide[CASING_REPAIRS_KEY] = kept
    else:
        slide.pop(CASING_REPAIRS_KEY, None)


__all__ = [
    "CASING_REPAIRS_KEY",
    "CASING_REPAIR_MESSAGE",
    "apply_sentence_case_repair",
    "casing_marker_violations",
    "drop_casing_repair_markers",
]
