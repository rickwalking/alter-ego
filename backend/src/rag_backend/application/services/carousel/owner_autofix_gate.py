"""Turn a repaired checkpoint copy into one gate patch.

The autopilot repairs a content or design gate before it revises it: the
plan runs over the checkpoint's ``localized_slides`` and the changed
slides go through the reviewer-edit path. That path re-validates and keeps
``slide_drafts``, ``translations_en`` and the content-gate report in step with
the repaired copy, so the next gate read sees the same verdict the engine
will enforce on approve.

No DB, no LLM.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import structlog

from rag_backend.application.services.carousel.presentation_review_edits import (
    apply_localized_slide_edits,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_FIXED,
    AUTOFIX_STATUS_NOTHING_TO_FIX,
    LOG_AUTOFIX_GATE_NOOP,
    LOG_AUTOFIX_GATE_REPAIRED,
)
from rag_backend.domain.constants.carousel_presentation import SEVERITY_BLOCKER
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_PRESENTATION_VALIDATION,
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_VIOLATIONS,
)

logger = structlog.get_logger()

_CODE = "code"
_SEVERITY = "severity"


@dataclass(frozen=True)
class GatePatch:
    """The checkpoint patch and the blocking rules it fixed or left."""

    updates: dict[str, object]
    fixed_rules: tuple[str, ...]
    remaining_rules: tuple[str, ...]
    translation_failed: bool = False


@dataclass(frozen=True)
class GateRepairResult:
    """What the gate repair fixed and which blocking rules are left."""

    status: str
    fixed_rules: tuple[str, ...] = ()
    remaining_rules: tuple[str, ...] = ()
    translation_failed: bool = False


@dataclass(frozen=True)
class GatePatchInput:
    """The checkpoint state, its copy before the plan, and the repaired copy."""

    state: Mapping[str, object]
    before: list[dict[str, object]]
    after: list[dict[str, object]]


def _changed(source: GatePatchInput) -> list[dict[str, object]]:
    before = {record.get(STATE_FIELD_SLIDE_INDEX): record for record in source.before}
    return [
        record
        for record in source.after
        if before.get(record.get(STATE_FIELD_SLIDE_INDEX)) != record
    ]


def blocking_rules(report: object) -> tuple[str, ...]:
    """Blocking rule ids of one validation report, in order, without repeats."""
    raw = report.get(STATE_FIELD_VIOLATIONS) if isinstance(report, Mapping) else None
    if not isinstance(raw, list):
        return ()
    codes: list[str] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        severity = item.get(_SEVERITY) or SEVERITY_BLOCKER
        code = item.get(_CODE)
        if severity == SEVERITY_BLOCKER and isinstance(code, str) and code:
            codes.append(code)
    return tuple(dict.fromkeys(codes))


def gate_patch(source: GatePatchInput) -> GatePatch | None:
    """The patch for the changed slides; None when the plan changed nothing."""
    edits = _changed(source)
    if not edits:
        return None
    updates = apply_localized_slide_edits(source.state, edits)
    previous = blocking_rules(source.state.get(STATE_FIELD_PRESENTATION_VALIDATION))
    remaining = blocking_rules(updates.get(STATE_FIELD_PRESENTATION_VALIDATION))
    fixed = tuple(rule for rule in previous if rule not in remaining)
    return GatePatch(updates=updates, fixed_rules=fixed, remaining_rules=remaining)


def gate_noop(project_id: str, state: Mapping[str, object]) -> GateRepairResult:
    """Nothing to repair: report the blocking rules the revise must address."""
    remaining = blocking_rules(state.get(STATE_FIELD_PRESENTATION_VALIDATION))
    logger.info(LOG_AUTOFIX_GATE_NOOP, project_id=project_id, remaining=list(remaining))
    return GateRepairResult(
        status=AUTOFIX_STATUS_NOTHING_TO_FIX, remaining_rules=remaining
    )


def gate_fixed(project_id: str, patch: GatePatch) -> GateRepairResult:
    """The patch was written: log and report what it fixed."""
    logger.info(
        LOG_AUTOFIX_GATE_REPAIRED,
        project_id=project_id,
        fixed_rules=list(patch.fixed_rules),
        remaining_rules=list(patch.remaining_rules),
        translation_failed=patch.translation_failed,
    )
    return GateRepairResult(
        status=AUTOFIX_STATUS_FIXED,
        fixed_rules=patch.fixed_rules,
        remaining_rules=patch.remaining_rules,
        translation_failed=patch.translation_failed,
    )


__all__ = [
    "GatePatch",
    "GatePatchInput",
    "GateRepairResult",
    "blocking_rules",
    "gate_fixed",
    "gate_noop",
    "gate_patch",
]
