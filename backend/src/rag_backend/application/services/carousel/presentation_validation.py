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
    ValidationFieldContext,
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


@dataclass
class _ValidationCtx:
    """Shared context for slide payload validation helpers."""

    locale: str
    slide_index: int | None
    violations: list[SlideValidationViolation]
    allowlist: frozenset[str]
    policy: CarouselPresentationPolicy


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


@dataclass(frozen=True)
class ValidatePayloadCommand:
    """Command to validate a single slide payload."""

    payload: Mapping[str, object]
    locale: str
    policy: CarouselPresentationPolicy | None = None
    slide_index: int | None = None


@dataclass(frozen=True)
class BoundedRepairCommand:
    """Command for a single bounded repair attempt."""

    request: BoundedRepairRequest
    repair_fn: RepairFn | None = None
    timeout_seconds: int = REPAIR_TIMEOUT_SECONDS_DEFAULT
    policy: CarouselPresentationPolicy | None = None


def _validate_en_heading_case(
    heading: str,
    policy: CarouselPresentationPolicy,
    ctx: _ValidationCtx,
) -> None:
    """Validate that EN headings use sentence case."""
    if ctx.locale != LANGUAGE_EN:
        return
    first_alpha = first_cased_alpha(heading)
    allowlisted = heading.strip() in policy.intentional_lowercase_allowlist
    if first_alpha is not None and first_alpha.islower() and not allowlisted:
        ctx.violations.append(
            SlideValidationViolation(
                code=VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
                message="English heading must start with an uppercase letter",
                slide_index=ctx.slide_index,
                locale=ctx.locale,
                field="heading",
            )
        )


def _validate_heading_not_in_body(
    heading: str,
    body: str,
    ctx: _ValidationCtx,
) -> None:
    """Validate that body does not repeat heading text."""
    normalized_heading = heading.strip().casefold()
    normalized_body = body.strip().casefold()
    if normalized_heading and normalized_heading in normalized_body:
        ctx.violations.append(
            SlideValidationViolation(
                code=VIOLATION_HEADING_REPEATED_IN_BODY,
                message="Body copy must not repeat the heading text",
                slide_index=ctx.slide_index,
                locale=ctx.locale,
                field="body",
            )
        )


def _validate_copy_budgets(
    slide_type: str,
    texts: tuple[str, str],
    ctx: _ValidationCtx,
) -> None:
    """Validate heading and body copy budgets."""
    heading, body = texts
    heading_budget = heading_budget_for_slide_type(slide_type, ctx.policy)
    if heading_budget is not None:
        budget_violation = validate_copy_budget(
            ValidationFieldContext(
                text=heading,
                field="heading",
                budget=heading_budget,
                too_long_code=VIOLATION_HEADING_TOO_LONG,
                locale=ctx.locale,
                slide_index=ctx.slide_index,
            )
        )
        if budget_violation is not None:
            ctx.violations.append(budget_violation)
    body_budget = body_budget_for_slide_type(slide_type, ctx.policy)
    if body_budget is not None:
        budget_violation = validate_copy_budget(
            ValidationFieldContext(
                text=body,
                field="body",
                budget=body_budget,
                too_long_code=VIOLATION_BODY_TOO_LONG,
                locale=ctx.locale,
                slide_index=ctx.slide_index,
            )
        )
        if budget_violation is not None:
            ctx.violations.append(budget_violation)


def _validate_structured_sections(
    payload: Mapping[str, object],
    policy: CarouselPresentationPolicy,
    ctx: _ValidationCtx,
) -> None:
    """Validate all structured item sections (features, summary_points, actions)."""
    sections: list[tuple[str, str, str]] = [
        ("features", "feature_title", "feature_body"),
        ("summary_points", "summary_point_title", "summary_point_body"),
        ("actions", "closing_action_title", "closing_action_body"),
    ]
    for field, title_key, body_key in sections:
        ctx.violations.extend(
            validate_structured_items(
                ValidationFieldContext(
                    items=payload.get(field),
                    allowlist=ctx.allowlist,
                    title_budget=policy.copy_budgets.get(title_key),
                    body_budget=policy.copy_budgets.get(body_key),
                    locale=ctx.locale,
                    slide_index=ctx.slide_index,
                    field_prefix=field,
                )
            )
        )


def validate_slide_payload(
    command: ValidatePayloadCommand,
) -> list[SlideValidationViolation]:
    """Validate one slide payload deterministically."""
    active_policy = command.policy or load_presentation_policy(
        DEFAULT_PRESENTATION_POLICY_VERSION
    )
    slide_type = str(
        command.payload.get("slide_type") or command.payload.get("type") or ""
    )
    heading = str(command.payload.get("heading") or "")
    body = str(command.payload.get("body") or "")
    violations: list[SlideValidationViolation] = []
    ctx = _ValidationCtx(
        locale=command.locale,
        slide_index=command.slide_index,
        violations=violations,
        allowlist=frozenset(active_policy.lucide_icon_allowlist),
        policy=active_policy,
    )

    if not heading.strip():
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_HEADING_EMPTY,
                message="Heading is required",
                slide_index=command.slide_index,
                locale=command.locale,
                field="heading",
            )
        )

    violations.extend(
        validate_visible_field(
            ValidationFieldContext(
                text=heading,
                field="heading",
                locale=command.locale,
                slide_index=command.slide_index,
            )
        )
    )
    violations.extend(
        validate_visible_field(
            ValidationFieldContext(
                text=body,
                field="body",
                locale=command.locale,
                slide_index=command.slide_index,
            )
        )
    )
    _validate_en_heading_case(heading, active_policy, ctx)
    _validate_heading_not_in_body(heading, body, ctx)
    _validate_copy_budgets(slide_type, (heading, body), ctx)
    _validate_structured_sections(command.payload, active_policy, ctx)
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
    command: BoundedRepairCommand,
) -> BoundedRepairResult:
    """Attempt at most one bounded repair for a locale, then revalidate."""
    violations_before = tuple(command.request.violations)
    if not violations_before or command.repair_fn is None:
        return BoundedRepairResult(
            payload=command.request.payload,
            repair_attempted=False,
            violations_before=violations_before,
            violations_after=violations_before,
        )

    try:
        repaired_payload = await asyncio.wait_for(
            command.repair_fn(
                command.request.payload, violations_before, command.request.locale
            ),
            timeout=command.timeout_seconds,
        )
    except TimeoutError:
        return BoundedRepairResult(
            payload=command.request.payload,
            repair_attempted=True,
            violations_before=violations_before,
            violations_after=violations_before,
            timed_out=True,
        )

    if repaired_payload is None:
        return BoundedRepairResult(
            payload=command.request.payload,
            repair_attempted=True,
            violations_before=violations_before,
            violations_after=violations_before,
        )

    slide_index_value = command.request.payload.get("slide_index")
    slide_index = slide_index_value if isinstance(slide_index_value, int) else None
    violations_after = tuple(
        validate_slide_payload(
            ValidatePayloadCommand(
                repaired_payload,
                locale=command.request.locale,
                policy=command.policy,
                slide_index=slide_index,
            )
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
    "BoundedRepairCommand",
    "BoundedRepairRequest",
    "BoundedRepairResult",
    "ValidatePayloadCommand",
    "build_validation_report",
    "contains_drafting_scaffold",
    "contains_forbidden_dash",
    "contains_visible_emoji",
    "run_bounded_repair",
    "validate_bilingual_shape_parity",
    "validate_slide_payload",
]
