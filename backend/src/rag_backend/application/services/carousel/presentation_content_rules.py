"""Objective quality-rubric validators for slide structure and markup (AE-0366).

Each rule mirrors one objective item of the contract's ``quality_rubric`` and is
active only when the loaded policy declares a severity for its code (v2+), so a
v1 project keeps its legacy semantics:

- ``body_empty``: the slide renders only its heading. Intro needs a body;
  content needs a body or a filled features list; summary/closing need a body
  or their items. The CTA is exempt through the policy's casing exemptions.
- ``closing_actions_missing``: a closing slide has fewer than 3 complete actions.
- ``summary_points_missing``: a summary slide has fewer than 3 complete points.
- ``emphasis_markup_invalid``: visible copy uses an HTML tag other than
  ``<strong>``, unbalanced/nested ``<strong>`` tags, or the bare ``strong ...
  /strong`` residue a tag-stripping sanitizer leaves behind.
- ``translation_not_english``: the EN heading/body is the PT copy pasted as-is.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.carousel import (
    LANGUAGE_EN,
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.carousel_presentation import (
    MIN_CLOSING_ACTIONS,
    MIN_CONTENT_FEATURES_WITHOUT_BODY,
    MIN_SUMMARY_POINTS,
    MIN_UNTRANSLATED_COMPARE_CHARS,
    VIOLATION_BODY_EMPTY,
    VIOLATION_CLOSING_ACTIONS_MISSING,
    VIOLATION_EMPHASIS_MARKUP_INVALID,
    VIOLATION_SUMMARY_POINTS_MISSING,
    VIOLATION_TRANSLATION_NOT_ENGLISH,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationViolation,
    ViolationSeverity,
)

_FIELD_HEADING = "heading"
_FIELD_BODY = "body"
_KEY_FEATURES = "features"
_KEY_ACTIONS = "actions"
_KEY_SUMMARY_POINTS = "summary_points"
_ITEM_TITLE = "title"
_ITEM_BODY = "body"
_ITEM_LIST_FIELDS = (_KEY_FEATURES, _KEY_SUMMARY_POINTS, _KEY_ACTIONS)
_SLIDE_TYPE_KEYS = ("slide_type", "type")
_ALLOWED_TAG = "strong"
_TAG_PATTERN = re.compile(r"<\s*(/?)\s*([A-Za-z][A-Za-z0-9]*)[^>]*>")
# Residue of a sanitizer that stripped "<" and ">": "strongword/strong".
_MANGLED_TAG_PATTERN = re.compile(r"(?<!<)/strong\b", flags=re.IGNORECASE)
_WHITESPACE_PATTERN = re.compile(r"\s+")

_MESSAGES: dict[str, str] = {
    VIOLATION_BODY_EMPTY: "Slide renders only its heading: the body copy is empty",
    VIOLATION_CLOSING_ACTIONS_MISSING: (
        f"Closing slide needs at least {MIN_CLOSING_ACTIONS} actions with a "
        "title and a body"
    ),
    VIOLATION_SUMMARY_POINTS_MISSING: (
        f"Summary slide needs at least {MIN_SUMMARY_POINTS} points with a "
        "title and a body"
    ),
    VIOLATION_EMPHASIS_MARKUP_INVALID: (
        "Emphasis must use balanced <strong>...</strong> tags only"
    ),
    VIOLATION_TRANSLATION_NOT_ENGLISH: (
        "English copy is identical to the Portuguese copy (not translated)"
    ),
}


@dataclass(frozen=True)
class ContentRuleCommand:
    """Inputs for the structural rubric checks of one locale payload."""

    payload: Mapping[str, object]
    locale: str
    policy: CarouselPresentationPolicy
    slide_index: int | None = None


def _slide_type(payload: Mapping[str, object]) -> str:
    for key in _SLIDE_TYPE_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    return value if isinstance(value, str) else ""


def _items(payload: Mapping[str, object], field: str) -> list[Mapping[str, object]]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _complete_items(payload: Mapping[str, object], *fields: str) -> int:
    count = 0
    for field in fields:
        for item in _items(payload, field):
            if _text(item, _ITEM_TITLE).strip() and _text(item, _ITEM_BODY).strip():
                count += 1
    return count


def _active(policy: CarouselPresentationPolicy, code: str, slide_type: str) -> bool:
    if code not in policy.rule_severities:
        return False
    rule = policy.casing_rule(code)
    return rule is None or rule.applies_to(slide_type)


def _violation(
    command: ContentRuleCommand, code: str, field: str
) -> SlideValidationViolation:
    severity: ViolationSeverity = (
        "warning" if command.policy.is_casing_warning(code) else "blocker"
    )
    return SlideValidationViolation(
        code=code,
        message=_MESSAGES[code],
        slide_index=command.slide_index,
        locale=command.locale,
        field=field,
        severity=severity,
    )


def _body_is_empty(payload: Mapping[str, object], slide_type: str) -> bool:
    if _text(payload, _FIELD_BODY).strip():
        return False
    if slide_type == SLIDE_TYPE_CONTENT:
        complete = _complete_items(payload, _KEY_FEATURES)
        return complete < MIN_CONTENT_FEATURES_WITHOUT_BODY
    if slide_type in {SLIDE_TYPE_SUMMARY, SLIDE_TYPE_CLOSING}:
        return _complete_items(payload, *_ITEM_LIST_FIELDS) == 0
    return True


def _structure_codes(payload: Mapping[str, object], slide_type: str) -> list[str]:
    codes: list[str] = []
    if _body_is_empty(payload, slide_type):
        codes.append(VIOLATION_BODY_EMPTY)
    if (
        slide_type == SLIDE_TYPE_CLOSING
        and _complete_items(payload, _KEY_ACTIONS, _KEY_FEATURES) < MIN_CLOSING_ACTIONS
    ):
        codes.append(VIOLATION_CLOSING_ACTIONS_MISSING)
    if (
        slide_type == SLIDE_TYPE_SUMMARY
        and _complete_items(payload, _KEY_SUMMARY_POINTS) < MIN_SUMMARY_POINTS
    ):
        codes.append(VIOLATION_SUMMARY_POINTS_MISSING)
    return codes


def emphasis_markup_is_valid(text: str) -> bool:
    """True when the only HTML is balanced, non-nested ``<strong>`` tags."""
    if _MANGLED_TAG_PATTERN.search(_TAG_PATTERN.sub("", text)):
        return False
    depth = 0
    for match in _TAG_PATTERN.finditer(text):
        closing, name = match.group(1) == "/", match.group(2).lower()
        if name != _ALLOWED_TAG:
            return False
        if closing == (depth == 0):
            return False
        depth = 0 if closing else 1
    return depth == 0


def _visible_fields(payload: Mapping[str, object]) -> list[tuple[str, str]]:
    fields = [
        (_FIELD_HEADING, _text(payload, _FIELD_HEADING)),
        (_FIELD_BODY, _text(payload, _FIELD_BODY)),
    ]
    for list_field in _ITEM_LIST_FIELDS:
        for index, item in enumerate(_items(payload, list_field)):
            fields.extend(
                (f"{list_field}[{index}].{key}", _text(item, key))
                for key in (_ITEM_TITLE, _ITEM_BODY)
            )
    return fields


def content_rule_violations(
    command: ContentRuleCommand,
) -> list[SlideValidationViolation]:
    """Structure + markup rubric violations for one locale payload (v2+)."""
    slide_type = _slide_type(command.payload)
    violations = [
        _violation(command, code, _FIELD_BODY)
        for code in _structure_codes(command.payload, slide_type)
        if _active(command.policy, code, slide_type)
    ]
    if _active(command.policy, VIOLATION_EMPHASIS_MARKUP_INVALID, slide_type):
        violations.extend(
            _violation(command, VIOLATION_EMPHASIS_MARKUP_INVALID, field)
            for field, text in _visible_fields(command.payload)
            if not emphasis_markup_is_valid(text)
        )
    return violations


def _normalized(text: str) -> str:
    plain = _TAG_PATTERN.sub("", text)
    return _WHITESPACE_PATTERN.sub(" ", plain).strip().casefold()


@dataclass(frozen=True)
class TranslationCheckCommand:
    """PT/EN payload pair for the not-translated check."""

    pt_payload: Mapping[str, object]
    en_payload: Mapping[str, object]
    policy: CarouselPresentationPolicy
    slide_index: int | None = None


def translation_violations(
    command: TranslationCheckCommand,
) -> list[SlideValidationViolation]:
    """Flag EN heading/body copy that is the PT copy pasted untranslated."""
    code = VIOLATION_TRANSLATION_NOT_ENGLISH
    if code not in command.policy.rule_severities:
        return []
    rule_command = ContentRuleCommand(
        payload=command.en_payload,
        locale=LANGUAGE_EN,
        policy=command.policy,
        slide_index=command.slide_index,
    )
    violations: list[SlideValidationViolation] = []
    for field in (_FIELD_HEADING, _FIELD_BODY):
        english = _normalized(_text(command.en_payload, field))
        portuguese = _normalized(_text(command.pt_payload, field))
        if len(english) >= MIN_UNTRANSLATED_COMPARE_CHARS and english == portuguese:
            violations.append(_violation(rule_command, code, field))
    return violations


__all__ = [
    "ContentRuleCommand",
    "TranslationCheckCommand",
    "content_rule_violations",
    "emphasis_markup_is_valid",
    "translation_violations",
]
