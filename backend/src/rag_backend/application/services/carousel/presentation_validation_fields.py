"""Field-level deterministic validators for carousel presentation payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

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


@dataclass(frozen=True)
class ValidationFieldContext:
    """Shared context for field-level validators."""

    text: str = ""
    field: str = ""
    locale: str | None = None
    slide_index: int | None = None
    budget: TextBudget | None = None
    too_long_code: str = ""
    icon_name: str | None = None
    allowlist: frozenset[str] = frozenset()
    items: object = None
    title_budget: TextBudget | None = None
    body_budget: TextBudget | None = None
    field_prefix: str = ""


def validate_visible_field(
    ctx: ValidationFieldContext,
) -> list[SlideValidationViolation]:
    """Validate visible text fields for emoji, dash, and scaffold rules."""
    violations: list[SlideValidationViolation] = []
    if contains_visible_emoji(ctx.text):
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
                message="Visible text must not contain decorative emoji",
                slide_index=ctx.slide_index,
                locale=ctx.locale,
                field=ctx.field,
            )
        )
    if contains_forbidden_dash(ctx.text):
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_DASH_PUNCTUATION_FORBIDDEN,
                message="Visible text must not contain em dash or en dash",
                slide_index=ctx.slide_index,
                locale=ctx.locale,
                field=ctx.field,
            )
        )
    if contains_drafting_scaffold(ctx.text):
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_DRAFTING_SCAFFOLD_PRESENT,
                message="Visible text must not contain drafting scaffold labels",
                slide_index=ctx.slide_index,
                locale=ctx.locale,
                field=ctx.field,
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
    ctx: ValidationFieldContext,
) -> SlideValidationViolation | None:
    """Validate character and optional line budgets for a field."""
    if ctx.budget is None:
        msg = "budget is required for this validator"
        raise ValueError(msg)
    if len(ctx.text) > ctx.budget.max_characters:
        return SlideValidationViolation(
            code=ctx.too_long_code,
            message=(
                f"{ctx.field} exceeds max {ctx.budget.max_characters} characters "
                f"(got {len(ctx.text)})"
            ),
            slide_index=ctx.slide_index,
            locale=ctx.locale,
            field=ctx.field,
        )
    if ctx.budget.max_lines is not None:
        line_count = count_rendered_lines(ctx.text)
        if line_count > ctx.budget.max_lines:
            return SlideValidationViolation(
                code=VIOLATION_COPY_TOO_MANY_LINES,
                message=(
                    f"{ctx.field} exceeds max {ctx.budget.max_lines} rendered lines "
                    f"(got {line_count})"
                ),
                slide_index=ctx.slide_index,
                locale=ctx.locale,
                field=ctx.field,
            )
    return None


def validate_icon_name(
    ctx: ValidationFieldContext,
) -> list[SlideValidationViolation]:
    """Validate structured Lucide icon_name markers."""
    if ctx.icon_name is None or not ctx.icon_name.strip():
        return []
    normalized = ctx.icon_name.strip()
    violations: list[SlideValidationViolation] = []
    if contains_visible_emoji(normalized):
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
                message="Structured icon markers must not use emoji",
                slide_index=ctx.slide_index,
                locale=ctx.locale,
                field=ctx.field,
            )
        )
    if normalized not in ctx.allowlist:
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_ICON_NAME_NOT_ALLOWLISTED,
                message=f"icon_name {normalized!r} is not in the Lucide allowlist",
                slide_index=ctx.slide_index,
                locale=ctx.locale,
                field=ctx.field,
            )
        )
    return violations


def validate_structured_items(
    ctx: ValidationFieldContext,
) -> list[SlideValidationViolation]:
    """Validate structured feature/summary/action item lists."""
    if not isinstance(ctx.items, list) or not ctx.items:
        return []
    violations: list[SlideValidationViolation] = []
    for index, item in enumerate(ctx.items):
        if not isinstance(item, Mapping):
            continue
        icon_name = resolve_structured_item_icon_name(item)
        violations.extend(
            validate_icon_name(
                ValidationFieldContext(
                    icon_name=icon_name,
                    allowlist=ctx.allowlist,
                    field=f"{ctx.field_prefix}[{index}].icon_name",
                    locale=ctx.locale,
                    slide_index=ctx.slide_index,
                )
            )
        )
        title = str(item.get("title") or "")
        body = str(item.get("body") or "")
        violations.extend(
            validate_visible_field(
                ValidationFieldContext(
                    text=title,
                    field=f"{ctx.field_prefix}[{index}].title",
                    locale=ctx.locale,
                    slide_index=ctx.slide_index,
                )
            )
        )
        violations.extend(
            validate_visible_field(
                ValidationFieldContext(
                    text=body,
                    field=f"{ctx.field_prefix}[{index}].body",
                    locale=ctx.locale,
                    slide_index=ctx.slide_index,
                )
            )
        )
        if ctx.title_budget is not None:
            budget_violation = validate_copy_budget(
                ValidationFieldContext(
                    text=title,
                    field=f"{ctx.field_prefix}[{index}].title",
                    budget=ctx.title_budget,
                    too_long_code=VIOLATION_HEADING_TOO_LONG,
                    locale=ctx.locale,
                    slide_index=ctx.slide_index,
                )
            )
            if budget_violation is not None:
                violations.append(budget_violation)
        if ctx.body_budget is not None:
            budget_violation = validate_copy_budget(
                ValidationFieldContext(
                    text=body,
                    field=f"{ctx.field_prefix}[{index}].body",
                    budget=ctx.body_budget,
                    too_long_code=VIOLATION_BODY_TOO_LONG,
                    locale=ctx.locale,
                    slide_index=ctx.slide_index,
                )
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
    "ValidationFieldContext",
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
