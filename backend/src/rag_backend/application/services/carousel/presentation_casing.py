"""Sentence-case + non-empty-body validation and deterministic casing repair.

AE-0312 introduced PT casing rules; AE-0366 (policy v3) makes them BLOCKING and extends them
to every rendered headline/body text in BOTH locales: the slide heading and
body plus the titles and bodies of structured items (features, summary points,
closing actions). The structural rubric rules (``body_empty`` and friends) live in
``presentation_content_rules``.

Rules, severities, per-slide-type exemptions and the proper-noun list live in
the presentation policy YAML (v2+). A v1 policy defines no casing rules, so it
reports no casing violations and receives no casing mutations.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.sentence_case import (
    capitalize_first_letter,
    capitalize_sentence_starts,
    has_lowercase_sentence,
    starts_lowercase,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_BODY_NOT_SENTENCE_CASE_EN,
    VIOLATION_BODY_NOT_SENTENCE_CASE_PT,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    VIOLATION_PROPER_NOUN_CASING,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationViolation,
    ViolationSeverity,
)

_FIELD_HEADING = "heading"
_FIELD_BODY = "body"
_ITEM_FIELD_TITLE = "title"
_ITEM_FIELD_BODY = "body"
_ITEM_LIST_FIELDS = ("features", "summary_points", "actions")
_SLIDE_TYPE_KEYS = ("slide_type", "type")

_HEADING_CODES: dict[str, str] = {
    LANGUAGE_PT: VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    LANGUAGE_EN: VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
}
_BODY_CODES: dict[str, str] = {
    LANGUAGE_PT: VIOLATION_BODY_NOT_SENTENCE_CASE_PT,
    LANGUAGE_EN: VIOLATION_BODY_NOT_SENTENCE_CASE_EN,
}
_CASE_MESSAGES: dict[str, str] = {
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT: (
        "Portuguese heading must start with an uppercase letter"
    ),
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN: (
        "English heading must start with an uppercase letter"
    ),
    VIOLATION_BODY_NOT_SENTENCE_CASE_PT: (
        "Portuguese body sentences must start with an uppercase letter"
    ),
    VIOLATION_BODY_NOT_SENTENCE_CASE_EN: (
        "English body sentences must start with an uppercase letter"
    ),
}
_PROPER_NOUN_MESSAGE = "Configured proper nouns must match their canonical casing"


@dataclass(frozen=True)
class CasingCheckCommand:
    """Inputs for casing validation of one locale payload."""

    payload: Mapping[str, object]
    locale: str
    policy: CarouselPresentationPolicy
    slide_index: int | None = None


@dataclass(frozen=True)
class CasingFinding:
    """One visible text field whose sentence case is wrong."""

    field: str
    code: str


@dataclass(frozen=True)
class _VisibleText:
    field: str
    text: str
    is_heading: bool


def _slide_type(payload: Mapping[str, object]) -> str:
    for key in _SLIDE_TYPE_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _field_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    return value if isinstance(value, str) else ""


def _items(
    payload: Mapping[str, object], list_field: str
) -> list[Mapping[str, object]]:
    raw = payload.get(list_field)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _visible_texts(payload: Mapping[str, object]) -> list[_VisibleText]:
    """Every rendered headline/body text of a locale payload."""
    texts = [
        _VisibleText(
            field=_FIELD_HEADING,
            text=_field_text(payload, _FIELD_HEADING),
            is_heading=True,
        ),
        _VisibleText(
            field=_FIELD_BODY,
            text=_field_text(payload, _FIELD_BODY),
            is_heading=False,
        ),
    ]
    for list_field in _ITEM_LIST_FIELDS:
        for index, item in enumerate(_items(payload, list_field)):
            prefix = f"{list_field}[{index}]"
            texts.extend(
                _VisibleText(
                    field=f"{prefix}.{key}",
                    text=_field_text(item, key),
                    is_heading=key == _ITEM_FIELD_TITLE,
                )
                for key in (_ITEM_FIELD_TITLE, _ITEM_FIELD_BODY)
            )
    return texts


def _rule_active(
    policy: CarouselPresentationPolicy, code: str, slide_type: str
) -> bool:
    rule = policy.casing_rule(code)
    return rule is not None and rule.applies_to(slide_type)


def _severity(policy: CarouselPresentationPolicy, code: str) -> ViolationSeverity:
    # The policy stores validated severities; narrow to the model Literal.
    return "warning" if policy.is_casing_warning(code) else "blocker"


def _case_code(locale: str, *, is_heading: bool) -> str | None:
    return (_HEADING_CODES if is_heading else _BODY_CODES).get(locale)


def sentence_case_findings(
    payload: Mapping[str, object],
    locale: str,
    policy: CarouselPresentationPolicy,
) -> list[CasingFinding]:
    """List the visible fields of one locale payload that start lowercase."""
    if not policy.has_casing_rules:
        return []
    allowlist = policy.intentional_lowercase_allowlist
    slide_type = _slide_type(payload)
    findings: list[CasingFinding] = []
    for visible in _visible_texts(payload):
        code = _case_code(locale, is_heading=visible.is_heading)
        if code is None or not _rule_active(policy, code, slide_type):
            continue
        check = starts_lowercase if visible.is_heading else has_lowercase_sentence
        if check(visible.text, allowlist):
            findings.append(CasingFinding(field=visible.field, code=code))
    return findings


def _proper_noun_pattern(noun: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(noun)}\b", flags=re.IGNORECASE)


def canonicalize_proper_nouns(text: str, proper_nouns: tuple[str, ...]) -> str:
    """Rewrite each configured proper noun to its canonical casing."""
    result = text
    for noun in proper_nouns:
        result = _proper_noun_pattern(noun).sub(noun, result)
    return result


def has_proper_noun_casing_issue(text: str, proper_nouns: tuple[str, ...]) -> bool:
    """Return True when a configured proper noun appears mis-cased."""
    for noun in proper_nouns:
        for match in _proper_noun_pattern(noun).finditer(text):
            if match.group(0) != noun:
                return True
    return False


def make_casing_violation(
    command: CasingCheckCommand,
    finding: CasingFinding,
    message: str,
) -> SlideValidationViolation:
    """Build a policy-severity violation for one casing finding."""
    return SlideValidationViolation(
        code=finding.code,
        message=message,
        slide_index=command.slide_index,
        locale=command.locale,
        field=finding.field,
        severity=_severity(command.policy, finding.code),
    )


def _is_en_heading(finding: CasingFinding) -> bool:
    # The slide heading in EN is already checked by validate_slide_payload's
    # always-on EN heading rule; skip it here to avoid a duplicate violation.
    return (
        finding.field == _FIELD_HEADING
        and finding.code == VIOLATION_HEADING_NOT_SENTENCE_CASE_EN
    )


def _proper_noun_violation(
    command: CasingCheckCommand,
    slide_type: str,
) -> SlideValidationViolation | None:
    code = VIOLATION_PROPER_NOUN_CASING
    if not _rule_active(command.policy, code, slide_type):
        return None
    proper_nouns = command.policy.proper_nouns
    for visible in _visible_texts(command.payload):
        if has_proper_noun_casing_issue(visible.text, proper_nouns):
            return make_casing_violation(
                command,
                CasingFinding(field=visible.field, code=code),
                _PROPER_NOUN_MESSAGE,
            )
    return None


def casing_violations(
    command: CasingCheckCommand,
) -> list[SlideValidationViolation]:
    """Collect sentence-case and proper-noun casing violations (v2+ only)."""
    if not command.policy.has_casing_rules:
        return []
    slide_type = _slide_type(command.payload)
    violations = [
        make_casing_violation(command, finding, _CASE_MESSAGES[finding.code])
        for finding in sentence_case_findings(
            command.payload, command.locale, command.policy
        )
        if not _is_en_heading(finding)
    ]
    proper_noun = _proper_noun_violation(command, slide_type)
    if proper_noun is not None:
        violations.append(proper_noun)
    return violations


def _repair_field(
    payload: dict[str, object],
    field: str,
    transform: Callable[[str], str],
) -> None:
    raw = payload.get(field)
    if not isinstance(raw, str) or not raw:
        return
    payload[field] = transform(raw)


@dataclass(frozen=True)
class _CaseTransforms:
    heading: Callable[[str], str]
    body: Callable[[str], str]


@dataclass(frozen=True)
class _ActiveRules:
    heading: bool
    body: bool
    proper_nouns: bool


def _active_rules(
    locale: str,
    slide_type: str,
    policy: CarouselPresentationPolicy,
) -> _ActiveRules:
    heading_code = _case_code(locale, is_heading=True)
    body_code = _case_code(locale, is_heading=False)
    return _ActiveRules(
        heading=heading_code is not None
        and _rule_active(policy, heading_code, slide_type),
        body=body_code is not None and _rule_active(policy, body_code, slide_type),
        proper_nouns=_rule_active(policy, VIOLATION_PROPER_NOUN_CASING, slide_type),
    )


def _case_transforms(
    locale: str,
    slide_type: str,
    policy: CarouselPresentationPolicy,
) -> _CaseTransforms:
    allowlist = policy.intentional_lowercase_allowlist
    active = _active_rules(locale, slide_type, policy)

    def _nouns(text: str) -> str:
        if not active.proper_nouns:
            return text
        return canonicalize_proper_nouns(text, policy.proper_nouns)

    def _heading(text: str) -> str:
        fixed = capitalize_first_letter(text, allowlist) if active.heading else text
        return _nouns(fixed)

    def _body(text: str) -> str:
        fixed = capitalize_sentence_starts(text, allowlist) if active.body else text
        return _nouns(fixed)

    return _CaseTransforms(heading=_heading, body=_body)


def _repair_items(
    payload: dict[str, object],
    transforms: _CaseTransforms,
) -> None:
    for list_field in _ITEM_LIST_FIELDS:
        raw = payload.get(list_field)
        if not isinstance(raw, list):
            continue
        repaired_items: list[object] = []
        for item in raw:
            if not isinstance(item, Mapping):
                repaired_items.append(item)
                continue
            row = dict(item)
            _repair_field(row, _ITEM_FIELD_TITLE, transforms.heading)
            _repair_field(row, _ITEM_FIELD_BODY, transforms.body)
            repaired_items.append(row)
        payload[list_field] = repaired_items


def repair_casing(
    payload: Mapping[str, object],
    locale: str,
    policy: CarouselPresentationPolicy,
) -> dict[str, object]:
    """Deterministically repair casing for one locale payload.

    Uppercases only the first letter of headings, item titles and body
    sentences (locale-safe: "à" -> "À"; digits and allowlisted tokens are left
    alone) and canonicalizes configured proper nouns in every visible field.
    Policy-version gated (a v1 policy returns the payload unchanged) and
    idempotent.
    """
    repaired = dict(payload)
    if not policy.has_casing_rules:
        return repaired
    transforms = _case_transforms(locale, _slide_type(repaired), policy)
    _repair_field(repaired, _FIELD_HEADING, transforms.heading)
    _repair_field(repaired, _FIELD_BODY, transforms.body)
    _repair_items(repaired, transforms)
    return repaired


def uppercase_sentence_starts(text: str) -> str:
    """Uppercase the first letter of every sentence, preserving markdown."""
    return capitalize_sentence_starts(text)


__all__ = [
    "CasingCheckCommand",
    "CasingFinding",
    "canonicalize_proper_nouns",
    "casing_violations",
    "has_proper_noun_casing_issue",
    "make_casing_violation",
    "repair_casing",
    "sentence_case_findings",
    "uppercase_sentence_starts",
]
