"""LLM quality rubric: parse it from the contract and render it into prompts.

AE-0366: the presentation contract's ``quality_rubric`` section is the single
source of truth for the checklist the content drafter and the EN translator
must satisfy. Every rubric item names the validator rule codes that enforce it;
the loader refuses a rubric item whose rule code has no declared severity, so a
prompt instruction can never drift away from its deterministic validator.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
    PresentationPolicyError,
    QualityRubricItem,
)
from rag_backend.domain.constants.presentation_policy import (
    ERR_PRESENTATION_POLICY_INVALID,
    ERR_PRESENTATION_POLICY_RULE_SEVERITY_MISSING,
)

RUBRIC_AUDIENCE_CONTENT = "content"
RUBRIC_AUDIENCE_TRANSLATION = "translation"

_KEY_RUBRIC_ID = "rubric_id"
_KEY_INSTRUCTION = "instruction"
_KEY_RULE_CODES = "rule_codes"
_KEY_AUDIENCES = "audiences"

RUBRIC_HEADER = "QUALITY RUBRIC (every item is mandatory):"
RUBRIC_SELF_CHECK = (
    "SELF-CHECK before you return the JSON: re-read every heading, body and "
    "item against each rubric item above, fix every miss, and only then return "
    "the JSON."
)


def _require_text(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return value.strip()


def _str_list(mapping: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value:
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return tuple(str(item) for item in value)


def _parse_item(
    raw: object,
    rule_severities: Mapping[str, str],
) -> QualityRubricItem:
    if not isinstance(raw, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    mapping = cast(dict[str, object], raw)
    rule_codes = _str_list(mapping, _KEY_RULE_CODES)
    if any(code not in rule_severities for code in rule_codes):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_RULE_SEVERITY_MISSING)
    return QualityRubricItem(
        rubric_id=_require_text(mapping, _KEY_RUBRIC_ID),
        instruction=_require_text(mapping, _KEY_INSTRUCTION),
        rule_codes=rule_codes,
        audiences=frozenset(_str_list(mapping, _KEY_AUDIENCES)),
    )


def parse_quality_rubric(
    raw_value: object,
    rule_severities: Mapping[str, str],
) -> tuple[QualityRubricItem, ...]:
    """Parse the optional ``quality_rubric`` list (v2+); v1 omits it."""
    if raw_value is None:
        return ()
    if not isinstance(raw_value, list):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return tuple(_parse_item(item, rule_severities) for item in raw_value)


def render_quality_rubric(
    policy: CarouselPresentationPolicy,
    audience: str,
) -> str:
    """Render the numbered rubric checklist + self-check for one prompt audience."""
    items = [item for item in policy.quality_rubric if audience in item.audiences]
    if not items:
        return ""
    lines = [RUBRIC_HEADER]
    lines.extend(
        f"{number}. {item.instruction}" for number, item in enumerate(items, start=1)
    )
    lines.append(RUBRIC_SELF_CHECK)
    return "\n".join(lines)


__all__ = [
    "RUBRIC_AUDIENCE_CONTENT",
    "RUBRIC_AUDIENCE_TRANSLATION",
    "RUBRIC_HEADER",
    "RUBRIC_SELF_CHECK",
    "parse_quality_rubric",
    "render_quality_rubric",
]
