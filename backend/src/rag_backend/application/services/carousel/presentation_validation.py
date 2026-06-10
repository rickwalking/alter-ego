"""Deterministic presentation validators and bounded repair orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_validation_fields import (
    body_budget_for_slide_type,
    contains_drafting_scaffold,
    contains_forbidden_dash,
    contains_visible_emoji,
    first_cased_alpha,
    heading_budget_for_slide_type,
    validate_copy_budget,
    validate_structured_items,
    validate_visible_field,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN
from rag_backend.domain.constants.carousel_presentation import (
    VALIDATION_STATUS_INVALID,
    VALIDATION_STATUS_VALID,
    VIOLATION_BODY_TOO_LONG,
    VIOLATION_HEADING_EMPTY,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
    VIOLATION_HEADING_REPEATED_IN_BODY,
    VIOLATION_HEADING_TOO_LONG,
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationReport,
    SlideValidationViolation,
)
from rag_backend.domain.models.carousel_presentation_adapters import (
    detect_translation_shape_mismatch,
)

REPAIR_TIMEOUT_SECONDS_DEFAULT = 60
REPAIR_MAX_ATTEMPTS_PER_LOCALE = 1

RepairFn = Callable[
    [Mapping[str, object], tuple[SlideValidationViolation, ...], str],
    Awaitable[Mapping[str, object] | None],
]


@dataclass(frozen=True)
class BoundedRepairRequest:
    """Single bounded repair attempt inputs for one locale."""

    locale: str
    payload: Mapping[str, object]
    violations: tuple[SlideValidationViolation, ...]


@dataclass(frozen=True)
class BoundedRepairResult:
    """Outcome of at most one repair attempt per locale."""

    payload: Mapping[str, object]
    repair_attempted: bool
    violations_before: tuple[SlideValidationViolation, ...]
    violations_after: tuple[SlideValidationViolation, ...]
    timed_out: bool = False


def validate_slide_payload(
    payload: Mapping[str, object],
    *,
    locale: str,
    policy: CarouselPresentationPolicy | None = None,
    slide_index: int | None = None,
) -> list[SlideValidationViolation]:
    """Validate one slide payload deterministically."""
    active_policy = policy or load_presentation_policy(DEFAULT_PRESENTATION_POLICY_VERSION)
    allowlist = frozenset(active_policy.lucide_icon_allowlist)
    slide_type = str(payload.get("slide_type") or payload.get("type") or "")
    heading = str(payload.get("heading") or "")
    body = str(payload.get("body") or "")
    violations: list[SlideValidationViolation] = []

    if not heading.strip():
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_HEADING_EMPTY,
                message="Heading is required",
                slide_index=slide_index,
                locale=locale,
                field="heading",
            )
        )

    violations.extend(
        validate_visible_field(
            text=heading,
            field="heading",
            locale=locale,
            slide_index=slide_index,
        )
    )
    violations.extend(
        validate_visible_field(
            text=body,
            field="body",
            locale=locale,
            slide_index=slide_index,
        )
    )

    if locale == LANGUAGE_EN:
        first_alpha = first_cased_alpha(heading)
        allowlisted = heading.strip() in active_policy.intentional_lowercase_allowlist
        if first_alpha is not None and first_alpha.islower() and not allowlisted:
            violations.append(
                SlideValidationViolation(
                    code=VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
                    message="English heading must start with an uppercase letter",
                    slide_index=slide_index,
                    locale=locale,
                    field="heading",
                )
            )

    normalized_heading = heading.strip().casefold()
    normalized_body = body.strip().casefold()
    if normalized_heading and normalized_heading in normalized_body:
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_HEADING_REPEATED_IN_BODY,
                message="Body copy must not repeat the heading text",
                slide_index=slide_index,
                locale=locale,
                field="body",
            )
        )

    heading_budget = heading_budget_for_slide_type(slide_type, active_policy)
    if heading_budget is not None:
        budget_violation = validate_copy_budget(
            text=heading,
            field="heading",
            budget=heading_budget,
            too_long_code=VIOLATION_HEADING_TOO_LONG,
            locale=locale,
            slide_index=slide_index,
        )
        if budget_violation is not None:
            violations.append(budget_violation)

    body_budget = body_budget_for_slide_type(slide_type, active_policy)
    if body_budget is not None:
        budget_violation = validate_copy_budget(
            text=body,
            field="body",
            budget=body_budget,
            too_long_code=VIOLATION_BODY_TOO_LONG,
            locale=locale,
            slide_index=slide_index,
        )
        if budget_violation is not None:
            violations.append(budget_violation)

    violations.extend(
        validate_structured_items(
            items=payload.get("features"),
            allowlist=allowlist,
            title_budget=active_policy.copy_budgets.get("feature_title"),
            body_budget=active_policy.copy_budgets.get("feature_body"),
            locale=locale,
            slide_index=slide_index,
            field_prefix="features",
        )
    )
    violations.extend(
        validate_structured_items(
            items=payload.get("summary_points"),
            allowlist=allowlist,
            title_budget=active_policy.copy_budgets.get("summary_point_title"),
            body_budget=active_policy.copy_budgets.get("summary_point_body"),
            locale=locale,
            slide_index=slide_index,
            field_prefix="summary_points",
        )
    )
    violations.extend(
        validate_structured_items(
            items=payload.get("actions"),
            allowlist=allowlist,
            title_budget=active_policy.copy_budgets.get("closing_action_title"),
            body_budget=active_policy.copy_budgets.get("closing_action_body"),
            locale=locale,
            slide_index=slide_index,
            field_prefix="actions",
        )
    )
    return violations


def validate_bilingual_shape_parity(
    pt_payload: Mapping[str, object],
    en_payload: Mapping[str, object],
    *,
    slide_index: int | None = None,
) -> SlideValidationViolation | None:
    """Validate PT/EN structured-extra shape parity."""
    mismatch = detect_translation_shape_mismatch(pt_payload, en_payload)
    if mismatch is None:
        return None
    return SlideValidationViolation(
        code=VIOLATION_TRANSLATION_SHAPE_MISMATCH,
        message=mismatch.message,
        slide_index=slide_index,
    )


def build_validation_report(
    violations: list[SlideValidationViolation],
    *,
    blocking: bool = True,
) -> SlideValidationReport:
    """Build a consistent validation report from collected violations."""
    if not violations:
        return SlideValidationReport(
            validation_status=VALIDATION_STATUS_VALID,
            validated_at=datetime.now(tz=UTC),
            blocking=False,
            violations=[],
        )
    return SlideValidationReport(
        validation_status=VALIDATION_STATUS_INVALID,
        validated_at=datetime.now(tz=UTC),
        blocking=blocking,
        violations=violations,
    )


async def run_bounded_repair(
    request: BoundedRepairRequest,
    repair_fn: RepairFn | None = None,
    *,
    timeout_seconds: int = REPAIR_TIMEOUT_SECONDS_DEFAULT,
    policy: CarouselPresentationPolicy | None = None,
) -> BoundedRepairResult:
    """Attempt at most one bounded repair for a locale, then revalidate."""
    violations_before = tuple(request.violations)
    if not violations_before or repair_fn is None:
        return BoundedRepairResult(
            payload=request.payload,
            repair_attempted=False,
            violations_before=violations_before,
            violations_after=violations_before,
        )

    try:
        repaired_payload = await asyncio.wait_for(
            repair_fn(request.payload, violations_before, request.locale),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        return BoundedRepairResult(
            payload=request.payload,
            repair_attempted=True,
            violations_before=violations_before,
            violations_after=violations_before,
            timed_out=True,
        )

    if repaired_payload is None:
        return BoundedRepairResult(
            payload=request.payload,
            repair_attempted=True,
            violations_before=violations_before,
            violations_after=violations_before,
        )

    slide_index_value = request.payload.get("slide_index")
    slide_index = slide_index_value if isinstance(slide_index_value, int) else None
    violations_after = tuple(
        validate_slide_payload(
            repaired_payload,
            locale=request.locale,
            policy=policy,
            slide_index=slide_index,
        )
    )
    return BoundedRepairResult(
        payload=repaired_payload,
        repair_attempted=True,
        violations_before=violations_before,
        violations_after=violations_after,
    )


__all__ = [
    "REPAIR_MAX_ATTEMPTS_PER_LOCALE",
    "REPAIR_TIMEOUT_SECONDS_DEFAULT",
    "BoundedRepairRequest",
    "BoundedRepairResult",
    "build_validation_report",
    "contains_drafting_scaffold",
    "contains_forbidden_dash",
    "contains_visible_emoji",
    "run_bounded_repair",
    "validate_bilingual_shape_parity",
    "validate_slide_payload",
]
