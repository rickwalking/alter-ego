"""Pure deterministic repair computation for a carousel's localized slides.

Wraps the existing bounded repair helpers (AE-0309 scaffold recovery, body
trim, canonical shape normalization; AE-0312 policy-gated casing) so the
repair endpoint and the drift reconciler share one side-effect-free
computation: validate → repair → re-validate → per-slide diff + fresh report.

No DB, no checkpoint, no locks — those live in the orchestrating service.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rag_backend.application.services.carousel.presentation_review_pipeline import (
    repair_localized_slides,
    validate_localized_slides,
    validation_report_to_dict,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationReport

# (slide_index, locale) — locale is None for slide-level violations (parity,
# parse markers) that are not attributable to a single locale payload.
_ViolationTarget = tuple[int | None, str | None]


@dataclass(frozen=True)
class RepairSlideDiff:
    """Per-slide/locale repair outcome: which rule codes were fixed / remain."""

    slide_index: int | None
    locale: str | None
    repaired_codes: tuple[str, ...] = ()
    remaining_codes: tuple[str, ...] = ()

    @property
    def repaired(self) -> bool:
        """True when at least one violation code was deterministically fixed."""
        return bool(self.repaired_codes)


@dataclass(frozen=True)
class RepairComputation:
    """Result of repairing a localized-slides list: copy + diffs + report."""

    repaired_slides: list[dict[str, object]]
    diffs: tuple[RepairSlideDiff, ...] = ()
    report: dict[str, object] = field(default_factory=dict)
    blocking: bool = False

    @property
    def changed(self) -> bool:
        """True when any slide/locale had a violation deterministically fixed."""
        return any(diff.repaired for diff in self.diffs)


def _codes_by_target(report: SlideValidationReport) -> dict[_ViolationTarget, set[str]]:
    """Group a report's violation codes by (slide_index, locale)."""
    grouped: dict[_ViolationTarget, set[str]] = {}
    for violation in report.violations:
        target: _ViolationTarget = (violation.slide_index, violation.locale)
        grouped.setdefault(target, set()).add(violation.code)
    return grouped


def _diff_for_target(
    target: _ViolationTarget,
    before: set[str],
    after: set[str],
) -> RepairSlideDiff:
    """Build the per-target diff of fixed vs still-remaining codes."""
    return RepairSlideDiff(
        slide_index=target[0],
        locale=target[1],
        repaired_codes=tuple(sorted(before - after)),
        remaining_codes=tuple(sorted(before & after)),
    )


def _build_diffs(
    before: SlideValidationReport,
    after: SlideValidationReport,
) -> tuple[RepairSlideDiff, ...]:
    """Diff pre-repair vs post-repair violation codes per (slide, locale)."""
    before_codes = _codes_by_target(before)
    after_codes = _codes_by_target(after)
    diffs = [
        _diff_for_target(target, codes, after_codes.get(target, set()))
        for target, codes in sorted(
            before_codes.items(), key=lambda item: (item[0][0] or 0, item[0][1] or "")
        )
    ]
    return tuple(diff for diff in diffs if diff.repaired or diff.remaining_codes)


async def compute_localized_repairs(
    localized_slides: list[dict[str, object]],
    *,
    policy_version: str | None = None,
) -> RepairComputation:
    """Validate, bounded-repair, and re-validate a localized-slides list."""
    active_version = policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    before = validate_localized_slides(localized_slides, policy_version=active_version)
    repaired = await repair_localized_slides(
        localized_slides, policy_version=active_version
    )
    after = validate_localized_slides(repaired, policy_version=active_version)
    return RepairComputation(
        repaired_slides=repaired,
        diffs=_build_diffs(before, after),
        report=validation_report_to_dict(after),
        blocking=after.blocking,
    )


__all__ = [
    "RepairComputation",
    "RepairSlideDiff",
    "compute_localized_repairs",
]
