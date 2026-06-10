"""Field-level deterministic validators for carousel presentation payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping

from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
    TextBudget,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_BODY_TOO_LONG,
    VIOLATION_COPY_TOO_MANY_LINES,
    VIOLATION_DASH_PUNCTUATION_FORBIDDEN,
    VIOLATION_DRAFTING_SCAFFOLD_PRESENT,
    VIOLATION_HEADING_TOO_LONG,
    VIOLATION_ICON_NAME_NOT_ALLOWLISTED,
    VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation
from rag_backend.domain.models.carousel_presentation_adapters import (
    resolve_structured_item_icon_name,
)

_EM_DASH = "\u2014"
_EN_DASH = "\u2013"
_EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F600-\U0001F64F]",
    flags=re.UNICODE,
)
_DRAFTING_SCAFFOLD_PATTERN = re.compile(
    r"\b(?:SLIDE\s*\d+|TITLE|BODY|KEY\s*POINTS)\s*:",
    flags=re.IGNORECASE,
)


def contains_visible_emoji(text: str) -> bool:
    """Return True when visible copy includes decorative emoji."""
    return bool(_EMOJI_PATTERN.search(text))


def contains_forbidden_dash(text: str) -> bool:
    """Return True when visible copy includes em dash or en dash."""
    return _EM_DASH in text or _EN_DASH in text


def contains_drafting_scaffold(text: str) -> bool:
    """Return True when visible copy includes drafting scaffold labels."""
    return bool(_DRAFTING_SCAFFOLD_PATTERN.search(text))


def first_cased_alpha(text: str) -> str | None:
    """Return the first cased alphabetic character in text."""
    for char in text.strip():
        if char.isalpha():
            return char
    return None


def validate_visible_field(
    *,
    text: str,
    field: str,
    locale: str | None,
    slide_index: int | None,
) -> list[SlideValidationViolation]:
    """Validate visible text fields for emoji, dash, and scaffold rules."""
    violations: list[SlideValidationViolation] = []
    if contains_visible_emoji(text):
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
                message="Visible text must not contain decorative emoji",
                slide_index=slide_index,
                locale=locale,
                field=field,
            )
        )
    if contains_forbidden_dash(text):
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_DASH_PUNCTUATION_FORBIDDEN,
                message="Visible text must not contain em dash or en dash",
                slide_index=slide_index,
                locale=locale,
                field=field,
            )
        )
    if contains_drafting_scaffold(text):
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_DRAFTING_SCAFFOLD_PRESENT,
                message="Visible text must not contain drafting scaffold labels",
                slide_index=slide_index,
                locale=locale,
                field=field,
            )
        )
    return violations


def count_rendered_lines(text: str) -> int:
    """Count non-empty rendered lines in visible copy."""
    stripped = text.strip()
    if not stripped:
        return 0
    lines = [line for line in stripped.splitlines() if line.strip()]
    return len(lines) if lines else 1


def validate_copy_budget(
    *,
    text: str,
    field: str,
    budget: TextBudget,
    too_long_code: str,
    locale: str | None,
    slide_index: int | None,
) -> SlideValidationViolation | None:
    """Validate character and optional line budgets for a field."""
    if len(text) > budget.max_characters:
        return SlideValidationViolation(
            code=too_long_code,
            message=(
                f"{field} exceeds max {budget.max_characters} characters "
                f"(got {len(text)})"
            ),
            slide_index=slide_index,
            locale=locale,
            field=field,
        )
    if budget.max_lines is not None:
        line_count = count_rendered_lines(text)
        if line_count > budget.max_lines:
            return SlideValidationViolation(
                code=VIOLATION_COPY_TOO_MANY_LINES,
                message=(
                    f"{field} exceeds max {budget.max_lines} rendered lines "
                    f"(got {line_count})"
                ),
                slide_index=slide_index,
                locale=locale,
                field=field,
            )
    return None


def validate_icon_name(
    *,
    icon_name: str | None,
    allowlist: frozenset[str],
    field: str,
    locale: str | None,
    slide_index: int | None,
) -> list[SlideValidationViolation]:
    """Validate structured Lucide icon_name markers."""
    if icon_name is None or not icon_name.strip():
        return []
    normalized = icon_name.strip()
    violations: list[SlideValidationViolation] = []
    if contains_visible_emoji(normalized):
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
                message="Structured icon markers must not use emoji",
                slide_index=slide_index,
                locale=locale,
                field=field,
            )
        )
    if normalized not in allowlist:
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_ICON_NAME_NOT_ALLOWLISTED,
                message=f"icon_name {normalized!r} is not in the Lucide allowlist",
                slide_index=slide_index,
                locale=locale,
                field=field,
            )
        )
    return violations


def validate_structured_items(
    *,
    items: object,
    allowlist: frozenset[str],
    title_budget: TextBudget | None,
    body_budget: TextBudget | None,
    locale: str | None,
    slide_index: int | None,
    field_prefix: str,
) -> list[SlideValidationViolation]:
    """Validate structured feature/summary/action item lists."""
    if not isinstance(items, list) or not items:
        return []
    violations: list[SlideValidationViolation] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            continue
        icon_name = resolve_structured_item_icon_name(item)
        violations.extend(
            validate_icon_name(
                icon_name=icon_name,
                allowlist=allowlist,
                field=f"{field_prefix}[{index}].icon_name",
                locale=locale,
                slide_index=slide_index,
            )
        )
        title = str(item.get("title") or "")
        body = str(item.get("body") or "")
        violations.extend(
            validate_visible_field(
                text=title,
                field=f"{field_prefix}[{index}].title",
                locale=locale,
                slide_index=slide_index,
            )
        )
        violations.extend(
            validate_visible_field(
                text=body,
                field=f"{field_prefix}[{index}].body",
                locale=locale,
                slide_index=slide_index,
            )
        )
        if title_budget is not None:
            budget_violation = validate_copy_budget(
                text=title,
                field=f"{field_prefix}[{index}].title",
                budget=title_budget,
                too_long_code=VIOLATION_HEADING_TOO_LONG,
                locale=locale,
                slide_index=slide_index,
            )
            if budget_violation is not None:
                violations.append(budget_violation)
        if body_budget is not None:
            budget_violation = validate_copy_budget(
                text=body,
                field=f"{field_prefix}[{index}].body",
                budget=body_budget,
                too_long_code=VIOLATION_BODY_TOO_LONG,
                locale=locale,
                slide_index=slide_index,
            )
            if budget_violation is not None:
                violations.append(budget_violation)
    return violations


def heading_budget_for_slide_type(
    slide_type: str,
    policy: CarouselPresentationPolicy,
) -> TextBudget | None:
    """Resolve heading budget for a slide type."""
    if slide_type == "intro":
        return policy.copy_budgets.get("intro_heading")
    if slide_type == "summary":
        return policy.copy_budgets.get("summary_heading")
    if slide_type == "content":
        return policy.copy_budgets.get("content_heading")
    return policy.copy_budgets.get("content_heading")


def body_budget_for_slide_type(
    slide_type: str,
    policy: CarouselPresentationPolicy,
) -> TextBudget | None:
    """Resolve body budget for a slide type."""
    if slide_type == "content":
        return policy.copy_budgets.get("content_body")
    if slide_type == "intro":
        return policy.copy_budgets.get("intro_subtitle")
    return None


__all__ = [
    "body_budget_for_slide_type",
    "contains_drafting_scaffold",
    "contains_forbidden_dash",
    "contains_visible_emoji",
    "count_rendered_lines",
    "first_cased_alpha",
    "heading_budget_for_slide_type",
    "validate_copy_budget",
    "validate_icon_name",
    "validate_structured_items",
    "validate_visible_field",
]
