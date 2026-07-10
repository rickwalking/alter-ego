"""Fail-closed content review chain: validate -> repair -> retry -> report.

AE-0309: the content phase validates every localized slide payload it builds.
Parse failures are first repaired deterministically (scaffold extraction,
shape normalization, bounded copy repair); slides that stay blocking get ONE
injectable LLM re-draft; anything still blocking is attached to the content
interrupt payload as a blocking per-slide validation report so the reviewer
sees the violations at the content step.

The chain keys strictly on the validation report's ``blocking`` flag: a
report with ``blocking=False`` (e.g. future warning-severity rules, AE-0312)
never consumes the LLM retry and never raises the blocking gate report.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

import structlog

from rag_backend.application.services.carousel.localized_slide_builder import (
    resolve_slide_index,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
    PresentationReviewBuildResult,
    build_presentation_review_result_async,
)
from rag_backend.application.services.carousel.slide_parse_failures import (
    SlideParseFailure,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_BLOCKING,
    STATE_FIELD_CONTENT_GATE_VALIDATION,
    STATE_FIELD_SLIDE_DRAFTS,
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_VIOLATIONS,
)

logger = structlog.get_logger(__name__)

# Structured log event: one per typed slide parse failure, tagged with the
# repair outcome so prod incidents like 38affb3e are observable at write time.
LOG_EVENT_SLIDE_PARSE_FAILED = "carousel_slide_parse_failed"
REPAIR_OUTCOME_DETERMINISTIC = "deterministic_repair"
REPAIR_OUTCOME_RETRY = "llm_retry"
REPAIR_OUTCOME_UNREPAIRED = "unrepaired"

SlideDraftRetryFn = Callable[[int], Awaitable[dict[str, object] | None]]


@dataclass(frozen=True)
class FailClosedReviewCommand:
    """Inputs for one fail-closed content review build."""

    project_id: str
    slide_drafts: list[dict[str, object]]
    translations_en: Mapping[int, dict[str, object]] | None = None
    policy_version: str | None = None
    retry_draft: SlideDraftRetryFn | None = None


def _report_dict(updates: Mapping[str, object]) -> dict[str, object]:
    report = updates.get(WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY)
    return report if isinstance(report, dict) else {}


def _is_blocking(updates: Mapping[str, object]) -> bool:
    """The fail-closed chain keys strictly on the report's blocking flag."""
    return _report_dict(updates).get(STATE_FIELD_BLOCKING) is True


def _blocking_slide_indices(updates: Mapping[str, object]) -> set[int]:
    violations = _report_dict(updates).get(STATE_FIELD_VIOLATIONS)
    if not isinstance(violations, list):
        return set()
    indices: set[int] = set()
    for violation in violations:
        if not isinstance(violation, dict):
            continue
        slide_index = violation.get(STATE_FIELD_SLIDE_INDEX)
        if isinstance(slide_index, int):
            indices.add(slide_index)
    return indices


def _log_parse_failure(
    project_id: str,
    failure: SlideParseFailure,
    repair_outcome: str,
) -> None:
    logger.warning(
        LOG_EVENT_SLIDE_PARSE_FAILED,
        project_id=project_id,
        slide_index=failure.slide_index,
        locale=failure.locale,
        reason=failure.reason,
        repair_outcome=repair_outcome,
    )


def _log_recovered_failures(
    project_id: str,
    result: PresentationReviewBuildResult,
) -> None:
    unrecovered = set(result.unrecovered_failures)
    for failure in result.parse_failures:
        if failure not in unrecovered:
            _log_parse_failure(project_id, failure, REPAIR_OUTCOME_DETERMINISTIC)


def _log_retry_outcomes(
    project_id: str,
    failures: tuple[SlideParseFailure, ...],
    final_updates: Mapping[str, object],
) -> None:
    still_blocking = (
        _blocking_slide_indices(final_updates) if _is_blocking(final_updates) else set()
    )
    for failure in failures:
        outcome = (
            REPAIR_OUTCOME_UNREPAIRED
            if failure.slide_index in still_blocking
            else REPAIR_OUTCOME_RETRY
        )
        _log_parse_failure(project_id, failure, outcome)


def _finalize(
    updates: dict[str, object],
    drafts: list[dict[str, object]] | None,
) -> dict[str, object]:
    """Attach (or clear) the content-gate report and any retried drafts."""
    final = dict(updates)
    final[STATE_FIELD_CONTENT_GATE_VALIDATION] = (
        dict(_report_dict(final)) if _is_blocking(final) else {}
    )
    if drafts is not None:
        final[STATE_FIELD_SLIDE_DRAFTS] = drafts
    return final


async def _replace_failing_drafts(
    command: FailClosedReviewCommand,
    failing: set[int],
) -> tuple[list[dict[str, object]], bool]:
    """Re-draft each failing slide at most once via the injectable retry."""
    retry = command.retry_draft
    drafts = [dict(draft) for draft in command.slide_drafts]
    if retry is None:
        return drafts, False
    replaced = False
    for position, draft in enumerate(drafts):
        slide_index = resolve_slide_index(draft, position + 1)
        if slide_index not in failing:
            continue
        fresh = await retry(slide_index)
        if isinstance(fresh, dict):
            drafts[position] = dict(fresh)
            replaced = True
    return drafts, replaced


async def _build_review(
    command: FailClosedReviewCommand,
    drafts: list[dict[str, object]],
) -> PresentationReviewBuildResult:
    return await build_presentation_review_result_async(
        drafts,
        translations_en=command.translations_en,
        policy_version=command.policy_version,
    )


async def _retry_blocking_slides(
    command: FailClosedReviewCommand,
    updates: Mapping[str, object],
) -> tuple[list[dict[str, object]], PresentationReviewBuildResult] | None:
    """Run the single bounded LLM retry pass for blocking slides."""
    if command.retry_draft is None:
        return None
    failing = _blocking_slide_indices(updates)
    if not failing:
        return None
    drafts, replaced = await _replace_failing_drafts(command, failing)
    if not replaced:
        return None
    return drafts, await _build_review(command, drafts)


async def build_fail_closed_review_updates(
    command: FailClosedReviewCommand,
) -> dict[str, object]:
    """Build content review updates with the fail-closed chain (AE-0309)."""
    result = await _build_review(command, command.slide_drafts)
    _log_recovered_failures(command.project_id, result)
    if not _is_blocking(result.updates):
        return _finalize(result.updates, drafts=None)
    retried = await _retry_blocking_slides(command, result.updates)
    if retried is None:
        _log_retry_outcomes(
            command.project_id, result.unrecovered_failures, result.updates
        )
        return _finalize(result.updates, drafts=None)
    drafts, retried_result = retried
    _log_retry_outcomes(
        command.project_id, result.unrecovered_failures, retried_result.updates
    )
    return _finalize(retried_result.updates, drafts=drafts)


__all__ = [
    "LOG_EVENT_SLIDE_PARSE_FAILED",
    "REPAIR_OUTCOME_DETERMINISTIC",
    "REPAIR_OUTCOME_RETRY",
    "REPAIR_OUTCOME_UNREPAIRED",
    "FailClosedReviewCommand",
    "SlideDraftRetryFn",
    "build_fail_closed_review_updates",
]
