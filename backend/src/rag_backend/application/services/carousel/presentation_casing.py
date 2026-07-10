"""PT sentence-case validation and deterministic casing repair (AE-0312).

Portuguese carousel copy is held to the English casing bar: headings and body
sentences start uppercase and configured proper nouns match their canonical
casing. Rules and the proper-noun list live in the presentation policy YAML
(v2+); a v1 project reports no casing violations and receives no casing
mutations. All three rules are warning-severity, so they surface in the review
panel without blocking approval.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.presentation_validation_fields import (
    first_cased_alpha,
)
from rag_backend.domain.constants.carousel import LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_BODY_NOT_SENTENCE_CASE_PT,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    VIOLATION_PROPER_NOUN_CASING,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationViolation,
    ViolationSeverity,
)

_FIELD_HEADING = "heading"
_FIELD_BODY = "body"
_SLIDE_TYPE_KEYS = ("slide_type", "type")

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
# Sentence boundary: end punctuation (incl. a trailing "..." run) then whitespace.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class CasingCheckCommand:
    """Inputs for casing validation of one locale payload."""

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


def _field_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    return value if isinstance(value, str) else ""


def _rule_active(
    policy: CarouselPresentationPolicy, code: str, slide_type: str
) -> bool:
    rule = policy.casing_rule(code)
    return rule is not None and rule.applies_to(slide_type)


def _severity(policy: CarouselPresentationPolicy, code: str) -> ViolationSeverity:
    # The policy stores validated severities; narrow to the model Literal.
    return "warning" if policy.is_casing_warning(code) else "blocker"


def _starts_lowercase(text: str, allowlist: frozenset[str]) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped in allowlist:
        return False
    first = first_cased_alpha(stripped)
    return first is not None and first.islower()


def _uppercase_first_visible_letter(text: str, start: int) -> str:
    """Uppercase the first visible letter at or after ``start`` (markdown-aware).

    Skips leading HTML tags and markdown emphasis markers (``**``/``*``/``_``),
    which are non-alphabetic, so the first *letter* is uppercased and the markup
    is left untouched. Idempotent when the first letter is already uppercase.
    """
    index = start
    length = len(text)
    while index < length:
        tag = _HTML_TAG_PATTERN.match(text, index)
        if tag is not None:
            index = tag.end()
            continue
        char = text[index]
        if char.isalpha():
            if char.islower():
                return text[:index] + char.upper() + text[index + 1 :]
            return text
        index += 1
    return text


def uppercase_sentence_starts(text: str) -> str:
    """Uppercase the first letter of every sentence, preserving markdown."""
    if not text:
        return text
    starts = [0, *[match.end() for match in _SENTENCE_BOUNDARY.finditer(text)]]
    result = text
    # Uppercasing is a 1-char-for-1-char swap, so boundary offsets stay valid.
    for start in starts:
        result = _uppercase_first_visible_letter(result, start)
    return result


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


@dataclass(frozen=True)
class _ViolationSpec:
    """A code + field + message triple for one casing violation."""

    code: str
    field: str
    message: str


@dataclass(frozen=True)
class _ScanContext:
    """Resolved per-slide inputs shared by the casing rule checks."""

    command: CasingCheckCommand
    slide_type: str
    allowlist: frozenset[str]

    @property
    def is_pt(self) -> bool:
        return self.command.locale == LANGUAGE_PT

    def rule_active(self, code: str) -> bool:
        return _rule_active(self.command.policy, code, self.slide_type)


def _make_violation(
    command: CasingCheckCommand,
    spec: _ViolationSpec,
) -> SlideValidationViolation:
    return SlideValidationViolation(
        code=spec.code,
        message=spec.message,
        slide_index=command.slide_index,
        locale=command.locale,
        field=spec.field,
        severity=_severity(command.policy, spec.code),
    )


def _heading_case_violation(
    ctx: _ScanContext,
    heading: str,
) -> SlideValidationViolation | None:
    code = VIOLATION_HEADING_NOT_SENTENCE_CASE_PT
    if not ctx.is_pt or not ctx.rule_active(code):
        return None
    if not _starts_lowercase(heading, ctx.allowlist):
        return None
    return _make_violation(
        ctx.command,
        _ViolationSpec(
            code,
            _FIELD_HEADING,
            "Portuguese heading must start with an uppercase letter",
        ),
    )


def _body_case_violation(
    ctx: _ScanContext,
    body: str,
) -> SlideValidationViolation | None:
    code = VIOLATION_BODY_NOT_SENTENCE_CASE_PT
    if not ctx.is_pt or not ctx.rule_active(code):
        return None
    sentences = _SENTENCE_BOUNDARY.split(body)
    if not any(_starts_lowercase(sentence, ctx.allowlist) for sentence in sentences):
        return None
    return _make_violation(
        ctx.command,
        _ViolationSpec(
            code,
            _FIELD_BODY,
            "Portuguese body sentences must start with an uppercase letter",
        ),
    )


def _proper_noun_violation(
    ctx: _ScanContext,
    texts: tuple[tuple[str, str], ...],
) -> SlideValidationViolation | None:
    code = VIOLATION_PROPER_NOUN_CASING
    if not ctx.rule_active(code):
        return None
    proper_nouns = ctx.command.policy.proper_nouns
    for field, text in texts:
        if has_proper_noun_casing_issue(text, proper_nouns):
            return _make_violation(
                ctx.command,
                _ViolationSpec(
                    code,
                    field,
                    "Configured proper nouns must match their canonical casing",
                ),
            )
    return None


def casing_violations(
    command: CasingCheckCommand,
) -> list[SlideValidationViolation]:
    """Collect PT sentence-case and proper-noun casing violations (v2+ only)."""
    if not command.policy.has_casing_rules:
        return []
    heading = _field_text(command.payload, _FIELD_HEADING)
    body = _field_text(command.payload, _FIELD_BODY)
    ctx = _ScanContext(
        command=command,
        slide_type=_slide_type(command.payload),
        allowlist=frozenset(command.policy.intentional_lowercase_allowlist),
    )
    candidates = [
        _heading_case_violation(ctx, heading),
        _body_case_violation(ctx, body),
        _proper_noun_violation(ctx, ((_FIELD_HEADING, heading), (_FIELD_BODY, body))),
    ]
    return [violation for violation in candidates if violation is not None]


def _repair_field(
    payload: dict[str, object],
    field: str,
    transform: Callable[[str], str],
) -> None:
    raw = payload.get(field)
    if not isinstance(raw, str) or not raw:
        return
    payload[field] = transform(raw)


def repair_casing(
    payload: Mapping[str, object],
    locale: str,
    policy: CarouselPresentationPolicy,
) -> dict[str, object]:
    """Deterministically repair casing violations for one locale payload.

    Policy-version gated: a v1 policy defines no casing rules, so the payload is
    returned unchanged. Idempotent — already-correct copy is a no-op.
    """
    repaired = dict(payload)
    if not policy.has_casing_rules:
        return repaired
    slide_type = _slide_type(repaired)
    if locale == LANGUAGE_PT and _rule_active(
        policy, VIOLATION_HEADING_NOT_SENTENCE_CASE_PT, slide_type
    ):
        _repair_field(repaired, _FIELD_HEADING, _uppercase_first_visible_letter_at_zero)
    if locale == LANGUAGE_PT and _rule_active(
        policy, VIOLATION_BODY_NOT_SENTENCE_CASE_PT, slide_type
    ):
        _repair_field(repaired, _FIELD_BODY, uppercase_sentence_starts)
    if _rule_active(policy, VIOLATION_PROPER_NOUN_CASING, slide_type):
        for field in (_FIELD_HEADING, _FIELD_BODY):
            _repair_field(
                repaired,
                field,
                lambda text: canonicalize_proper_nouns(text, policy.proper_nouns),
            )
    return repaired


def _uppercase_first_visible_letter_at_zero(text: str) -> str:
    return _uppercase_first_visible_letter(text, 0)


__all__ = [
    "CasingCheckCommand",
    "canonicalize_proper_nouns",
    "casing_violations",
    "has_proper_noun_casing_issue",
    "repair_casing",
    "uppercase_sentence_starts",
]
