"""The copy limits of one slide, read from the contract the validator enforces.

Pure: no LLM, no DB. Every number comes from the loaded presentation policy
through the validator's own resolvers (``heading_budget_for_slide_type``,
``body_budget_for_slide_type`` and the item budget keys of ``field_budget``),
plus the two word rules the validator applies when the policy declares them:
the hook heading's word limit (the PT heading of the slide whose contract role
is ``hook``, as the deck rule checks it) and the content body's minimum words.
The drafting instruction, the translation request and the shorten step all
render these limits, so a contract change moves every prompt with the validator.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.content_gate_repair_targets import (
    field_budget,
)
from rag_backend.application.services.carousel.presentation_content_rules import (
    rule_active,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
    TextBudget,
)
from rag_backend.application.services.carousel.presentation_validation_fields import (
    body_budget_for_slide_type,
    heading_budget_for_slide_type,
)
from rag_backend.domain.constants.carousel import (
    LANGUAGE_PT,
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.carousel_presentation import (
    MIN_CONTENT_BODY_WORDS,
    VIOLATION_BODY_TOO_SHORT,
)
from rag_backend.domain.constants.content_mode import HOOK_MAX_WORDS
from rag_backend.domain.constants.copy_budget_fit import (
    ITEM_FIELD_PATTERN,
    LIMIT_KEY_FIELD,
    LIMIT_KEY_MAX_CHARACTERS,
    LIMIT_KEY_MAX_LINES,
    LIMIT_KEY_MAX_WORDS,
    LIMIT_KEY_MIN_WORDS,
)
from rag_backend.domain.constants.presentation_roles import (
    ROLE_HOOK,
    VIOLATION_HOOK_WORD_LIMIT,
)

_HEADING = "heading"
_BODY = "body"
_ITEM_TITLE = "title"
_ITEM_BODY = "body"
_SLIDE_TYPE_KEY = "slide_type"
_ITEM_LISTS_BY_SLIDE_TYPE: dict[str, tuple[str, ...]] = {
    SLIDE_TYPE_CONTENT: ("features",),
    SLIDE_TYPE_SUMMARY: ("summary_points",),
    SLIDE_TYPE_CLOSING: ("actions",),
}


@dataclass(frozen=True)
class LimitScope:
    """Which slide the limits are for: its type, contract role and locale."""

    slide_type: str
    role: str | None = None
    locale: str = LANGUAGE_PT

    def hook_heading(self) -> bool:
        """True for the scope whose heading the hook word rule checks (PT only)."""
        return self.role == ROLE_HOOK and self.locale == LANGUAGE_PT


def role_at(policy: CarouselPresentationPolicy, slide_index: int) -> str | None:
    """The contract role of a slide position (None: no role)."""
    for slide in policy.slides:
        if slide.slide_number == slide_index:
            return slide.role
    return None


@dataclass(frozen=True)
class FieldLimit:
    """The limit of one field: characters, optional lines and word rules."""

    field: str
    max_characters: int
    max_lines: int | None = None
    max_words: int | None = None
    min_words: int | None = None

    def as_dict(self) -> dict[str, object]:
        """The limit as prompt data (absent rules are left out)."""
        entry: dict[str, object] = {
            LIMIT_KEY_FIELD: self.field,
            LIMIT_KEY_MAX_CHARACTERS: self.max_characters,
        }
        optional = {
            LIMIT_KEY_MAX_LINES: self.max_lines,
            LIMIT_KEY_MAX_WORDS: self.max_words,
            LIMIT_KEY_MIN_WORDS: self.min_words,
        }
        entry.update({key: value for key, value in optional.items() if value})
        return entry


def _word_rules(
    scope: LimitScope, field: str, policy: CarouselPresentationPolicy
) -> tuple[int | None, int | None]:
    """(max words, min words) the validator applies to this field, if any."""
    if field == _HEADING and scope.hook_heading():
        declared = VIOLATION_HOOK_WORD_LIMIT in policy.rule_severities
        return (HOOK_MAX_WORDS if declared else None), None
    slide_type = scope.slide_type
    if field != _BODY or slide_type != SLIDE_TYPE_CONTENT:
        return None, None
    if not rule_active(policy, VIOLATION_BODY_TOO_SHORT, slide_type):
        return None, None
    return None, MIN_CONTENT_BODY_WORDS


def _limit(
    field: str,
    budget: TextBudget | None,
    context: tuple[LimitScope, CarouselPresentationPolicy],
) -> FieldLimit | None:
    if budget is None:
        return None
    scope, policy = context
    max_words, min_words = _word_rules(scope, field, policy)
    return FieldLimit(
        field=field,
        max_characters=budget.max_characters,
        max_lines=budget.max_lines,
        max_words=max_words,
        min_words=min_words,
    )


def _item_limits(
    scope: LimitScope, policy: CarouselPresentationPolicy
) -> list[FieldLimit]:
    limits: list[FieldLimit] = []
    for list_field in _ITEM_LISTS_BY_SLIDE_TYPE.get(scope.slide_type, ()):
        for item_field in (_ITEM_TITLE, _ITEM_BODY):
            path = f"{list_field}[0].{item_field}"
            budget = field_budget({_SLIDE_TYPE_KEY: scope.slide_type}, path, policy)
            label = ITEM_FIELD_PATTERN.format(
                list_field=list_field, item_field=item_field
            )
            limit = _limit(label, budget, (scope, policy))
            if limit is not None:
                limits.append(limit)
    return limits


def slide_field_limits(
    scope: LimitScope, policy: CarouselPresentationPolicy
) -> tuple[FieldLimit, ...]:
    """Every field limit of one slide, in rendering order."""
    context = (scope, policy)
    slide_type = scope.slide_type
    limits = [
        _limit(_HEADING, heading_budget_for_slide_type(slide_type, policy), context),
        _limit(_BODY, body_budget_for_slide_type(slide_type, policy), context),
    ]
    found = [limit for limit in limits if limit is not None]
    return (*found, *_item_limits(scope, policy))


def field_limit(
    payload: Mapping[str, object],
    field: str,
    context: tuple[LimitScope, CarouselPresentationPolicy],
) -> FieldLimit | None:
    """The limit of one field path of a locale payload (None: no budget)."""
    return _limit(field, field_budget(payload, field, context[1]), context)


def limits_payload(
    scope: LimitScope, policy: CarouselPresentationPolicy
) -> list[dict[str, object]]:
    """The slide's limits as JSON-ready data (translation request, prompts)."""
    return [limit.as_dict() for limit in slide_field_limits(scope, policy)]


__all__ = [
    "FieldLimit",
    "LimitScope",
    "field_limit",
    "limits_payload",
    "role_at",
    "slide_field_limits",
]
