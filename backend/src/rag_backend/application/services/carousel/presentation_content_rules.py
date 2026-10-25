"""Objective quality-rubric validators for slide structure and markup.

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
- ``translation_not_english``: the EN heading/body is the PT copy pasted as-is,
  or is still Portuguese.

The TL;DR strip is rendered, so its language is checked too. A sanitizer that stripped
"<" and ">" leaves residue like "strongword/strong".
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.owner_autofix_text import (
    looks_portuguese,
)
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
    VIOLATION_WRONG_LANGUAGE,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationViolation,
    ViolationSeverity,
)

_FIELD_HEADING = "heading"
_FIELD_BODY = "body"
_FIELD_TLDR = "tldr_strip"
_KEY_FEATURES = "features"
_KEY_ACTIONS = "actions"
_KEY_SUMMARY_POINTS = "summary_points"
_ITEM_TITLE = "title"
_ITEM_BODY = "body"
_ITEM_LIST_FIELDS = (_KEY_FEATURES, _KEY_SUMMARY_POINTS, _KEY_ACTIONS)
_SLIDE_TYPE_KEYS = ("slide_type", "type")
_LISTS_OF_CODE: dict[str, tuple[str, ...]] = {
    VIOLATION_SUMMARY_POINTS_MISSING: (_KEY_SUMMARY_POINTS,),
    VIOLATION_CLOSING_ACTIONS_MISSING: (_KEY_ACTIONS, _KEY_FEATURES),
}
_ALLOWED_TAG = "strong"
_TAG_PATTERN = re.compile(r"<\s*(/?)\s*([A-Za-z][A-Za-z0-9]*)[^>]*>")
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


def slide_type_of(payload: Mapping[str, object]) -> str:
    """The payload's slide type (``slide_type`` or ``type``), or empty."""
    for key in _SLIDE_TYPE_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def text_of(payload: Mapping[str, object], field: str) -> str:
    """The string value of ``field``, or empty when absent or not a string."""
    value = payload.get(field)
    return value if isinstance(value, str) else ""


def _items(payload: Mapping[str, object], field: str) -> list[Mapping[str, object]]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def complete_item_count(payload: Mapping[str, object], *fields: str) -> int:
    """Items of the given lists that have both a title and a body."""
    count = 0
    for field in fields:
        for item in _items(payload, field):
            if text_of(item, _ITEM_TITLE).strip() and text_of(item, _ITEM_BODY).strip():
                count += 1
    return count


def rule_active(policy: CarouselPresentationPolicy, code: str, slide_type: str) -> bool:
    """True when the policy declares ``code`` and does not exempt the slide type."""
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
    if text_of(payload, _FIELD_BODY).strip():
        return False
    if slide_type == SLIDE_TYPE_CONTENT:
        complete = complete_item_count(payload, _KEY_FEATURES)
        return complete < MIN_CONTENT_FEATURES_WITHOUT_BODY
    if slide_type in {SLIDE_TYPE_SUMMARY, SLIDE_TYPE_CLOSING}:
        return complete_item_count(payload, *_ITEM_LIST_FIELDS) == 0
    return True


def _structure_codes(payload: Mapping[str, object], slide_type: str) -> list[str]:
    codes: list[str] = []
    if _body_is_empty(payload, slide_type):
        codes.append(VIOLATION_BODY_EMPTY)
    if (
        slide_type == SLIDE_TYPE_CLOSING
        and complete_item_count(payload, _KEY_ACTIONS, _KEY_FEATURES)
        < MIN_CLOSING_ACTIONS
    ):
        codes.append(VIOLATION_CLOSING_ACTIONS_MISSING)
    if (
        slide_type == SLIDE_TYPE_SUMMARY
        and complete_item_count(payload, _KEY_SUMMARY_POINTS) < MIN_SUMMARY_POINTS
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


def visible_fields(payload: Mapping[str, object]) -> list[tuple[str, str]]:
    """(field path, text) for the heading, the body and every item title/body."""
    fields = [
        (_FIELD_HEADING, text_of(payload, _FIELD_HEADING)),
        (_FIELD_BODY, text_of(payload, _FIELD_BODY)),
    ]
    for list_field in _ITEM_LIST_FIELDS:
        for index, item in enumerate(_items(payload, list_field)):
            fields.extend(
                (f"{list_field}[{index}].{key}", text_of(item, key))
                for key in (_ITEM_TITLE, _ITEM_BODY)
            )
    return fields


def language_fields(payload: Mapping[str, object]) -> list[tuple[str, str]]:
    """The visible fields plus the TL;DR strip: every text whose language counts.

    A PT TL;DR shipped as the EN one passed the gate because only
    heading, body and items were language-checked.
    """
    tldr = text_of(payload, _FIELD_TLDR)
    extra = [(_FIELD_TLDR, tldr)] if tldr.strip() else []
    return [*visible_fields(payload), *extra]


def _first_incomplete_item(
    payload: Mapping[str, object], list_fields: tuple[str, ...]
) -> str:
    """Where the editor shows a too-short item list: the first item missing a part.

    ``summary_points[i].title`` or ``summary_points[i].body`` for the first item
    without a title or a body; when every item is complete but there are too few,
    the list that holds them (the first list when none has items).
    """
    for list_field in list_fields:
        for index, item in enumerate(_items(payload, list_field)):
            for key in (_ITEM_TITLE, _ITEM_BODY):
                if not text_of(item, key).strip():
                    return f"{list_field}[{index}].{key}"
    holding = [field for field in list_fields if _items(payload, field)]
    return (holding or list(list_fields))[0]


def _structure_field(payload: Mapping[str, object], code: str) -> str:
    list_fields = _LISTS_OF_CODE.get(code)
    if list_fields is None:
        return _FIELD_BODY
    return _first_incomplete_item(payload, list_fields)


def content_rule_violations(
    command: ContentRuleCommand,
) -> list[SlideValidationViolation]:
    """Structure + markup rubric violations for one locale payload (v2+).

    ``body_empty`` points at the body; a too-short summary or closing list points
    at its first incomplete item, so the editor shows it under that item.
    """
    slide_type = slide_type_of(command.payload)
    violations = [
        _violation(command, code, _structure_field(command.payload, code))
        for code in _structure_codes(command.payload, slide_type)
        if rule_active(command.policy, code, slide_type)
    ]
    if rule_active(command.policy, VIOLATION_EMPHASIS_MARKUP_INVALID, slide_type):
        violations.extend(
            _violation(command, VIOLATION_EMPHASIS_MARKUP_INVALID, field)
            for field, text in visible_fields(command.payload)
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
    """Flag EN heading/body/TL;DR copy that is the PT copy pasted untranslated."""
    code = VIOLATION_TRANSLATION_NOT_ENGLISH
    if code not in command.policy.rule_severities:
        return []
    rule_command = ContentRuleCommand(
        payload=command.en_payload,
        locale=LANGUAGE_EN,
        policy=command.policy,
        slide_index=command.slide_index,
    )
    return [
        _violation(rule_command, code, field)
        for field in (_FIELD_HEADING, _FIELD_BODY, _FIELD_TLDR)
        if _untranslated(command, field)
    ]


def _untranslated(command: TranslationCheckCommand, field: str) -> bool:
    """EN copy pasted from PT, or EN copy that is still Portuguese.

    The second half is the autofix's ``looks_portuguese`` rule, so a policy
    without the ``wrong_language`` rule (v3) still flags Portuguese EN copy.

    When the wrong-language rule is active it reports Portuguese-looking EN, so this
    check does not report it again.
    """
    raw_english = text_of(command.en_payload, field)
    english = _normalized(raw_english)
    portuguese = _normalized(text_of(command.pt_payload, field))
    if len(english) >= MIN_UNTRANSLATED_COMPARE_CHARS and english == portuguese:
        return True
    if VIOLATION_WRONG_LANGUAGE in command.policy.rule_severities:
        return False
    return looks_portuguese(raw_english)


__all__ = [
    "ContentRuleCommand",
    "TranslationCheckCommand",
    "complete_item_count",
    "content_rule_violations",
    "emphasis_markup_is_valid",
    "language_fields",
    "rule_active",
    "slide_type_of",
    "text_of",
    "translation_violations",
    "visible_fields",
]
