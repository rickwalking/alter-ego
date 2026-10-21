"""Map a slide validation report onto per-field form violations."""

from __future__ import annotations

import re

from rag_backend.api.schemas.carousel_slide_edit import SlideFieldViolation
from rag_backend.domain.constants.carousel_slide_edit import (
    STRUCTURED_ITEM_FIELD_PATTERN,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationReport,
    SlideValidationViolation,
)

_STRUCTURED_ITEM_FIELD = re.compile(STRUCTURED_ITEM_FIELD_PATTERN)


def to_field_violation(violation: SlideValidationViolation) -> SlideFieldViolation:
    """Address one violation to its field, splitting a structured-item path."""
    field_violation = SlideFieldViolation(
        code=violation.code,
        message=violation.message,
        severity=violation.severity,
        slide_index=violation.slide_index,
        locale=violation.locale,
        field=violation.field,
    )
    match = _STRUCTURED_ITEM_FIELD.match(violation.field or "")
    if match is None:
        return field_violation
    return field_violation.model_copy(
        update={
            "item_list": match.group("list"),
            "item_index": int(match.group("index")),
            "item_field": match.group("field"),
        }
    )


def field_violations_from_report(
    report: SlideValidationReport,
) -> list[SlideFieldViolation]:
    """Every report violation, addressed to its form field."""
    return [to_field_violation(violation) for violation in report.violations]


__all__ = ["field_violations_from_report", "to_field_violation"]
