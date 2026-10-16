"""Model fix of failing slides after the deterministic repair (AE-0401).

Autopilot only, at the content and design gates. A gate that still fails on
content quality (blocking presentation rules) or on a low voice score after
the AE-0392 repair is not revised: each failing slide is rewritten by the
fast model, at most ``AUTOPILOT_AUTOFIX_ATTEMPTS`` times, the fixed slides are
written through the editorial facade, and the gate is read again. A clean
gate is approved; otherwise the run escalates to the owner with every slide
the fix gave up on. The revise budget is never spent on these reasons; other
reasons (research, outline, images, forbidden phrases) keep revise/escalate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import structlog

from rag_backend.modules.autopilot.application.gate_read import GateRead
from rag_backend.modules.autopilot.autofix_constants import (
    AUTOFIX_REASONS,
    ESCALATION_CAROUSEL_LINE,
    ESCALATION_HEADER,
    ESCALATION_MAX_SLIDES,
    ESCALATION_RULE_SEPARATOR,
    ESCALATION_SLIDE_LINE,
    ESCALATION_TEXT_ELLIPSIS,
    ESCALATION_TEXT_MAX_CHARS,
    LOG_FIELD_ATTEMPT,
    LOG_FIELD_FAILING_SLIDES,
    LOG_FIELD_OUTCOME,
    LOG_FIELD_RULES_AFTER,
    LOG_FIELD_RULES_BEFORE,
    LOG_FIELD_SLIDE,
    LOG_SLIDE_AUTOFIX,
    LOG_SLIDE_AUTOFIX_CONFLICT,
    LOG_SLIDE_AUTOFIX_ESCALATED,
)
from rag_backend.modules.autopilot.domain.autofix import (
    AutofixStatus,
    FailingSlide,
    SlideFixCommand,
    SlideFixer,
    SlideFixOutcome,
)
from rag_backend.modules.autopilot.domain.gate import (
    EditorialDriver,
    GateAction,
    PolicyDecision,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.quality_constants import QUALITY_GATES

logger = structlog.get_logger()

_FAILED_ACTIONS: frozenset[GateAction] = frozenset({
    GateAction.REVISE,
    GateAction.ESCALATE,
})


@dataclass(frozen=True, kw_only=True)
class SlideAutofixDependencies:
    """The driver to read the gate again and the optional model fixer."""

    editorial: EditorialDriver
    fixer: SlideFixer | None = None


def needs_model_fix(read: GateRead) -> bool:
    """A content/design gate failing on copy quality or a low voice score."""
    return (
        read.decision.action in _FAILED_ACTIONS
        and read.decision.reason in AUTOFIX_REASONS
        and read.snapshot.phase in QUALITY_GATES
    )


def _clip(text: str) -> str:
    flat = " ".join(text.split())
    if len(flat) <= ESCALATION_TEXT_MAX_CHARS:
        return flat
    return flat[:ESCALATION_TEXT_MAX_CHARS].rstrip() + ESCALATION_TEXT_ELLIPSIS


def _slide_line(slide: FailingSlide) -> str:
    return ESCALATION_SLIDE_LINE.format(
        slide=slide.slide_index,
        rules=ESCALATION_RULE_SEPARATOR.join(slide.rules),
        text=_clip(slide.text),
        attempts=slide.attempts,
    )


def escalation_detail(outcome: SlideFixOutcome) -> str:
    """The owner's list: each failing slide, its rules, text and attempts."""
    lines = [_slide_line(slide) for slide in outcome.failing[:ESCALATION_MAX_SLIDES]]
    if outcome.unfixable_rules:
        rules = ESCALATION_RULE_SEPARATOR.join(outcome.unfixable_rules)
        lines.append(ESCALATION_CAROUSEL_LINE.format(rules=rules))
    if not lines:
        return ""
    return "\n".join([ESCALATION_HEADER, *lines])


def _log(event: str, read: GateRead, extra: Mapping[str, object]) -> None:
    logger.info(
        event,
        run_id=str(read.run.run_id),
        project_id=read.run.carousel_project_id or "",
        phase=read.snapshot.phase,
        **extra,
    )


def _log_attempts(read: GateRead, outcome: SlideFixOutcome) -> None:
    for attempt in outcome.attempts:
        _log(
            LOG_SLIDE_AUTOFIX,
            read,
            {
                LOG_FIELD_SLIDE: attempt.slide_index,
                LOG_FIELD_ATTEMPT: attempt.attempt,
                LOG_FIELD_RULES_BEFORE: list(attempt.rules_before),
                LOG_FIELD_RULES_AFTER: list(attempt.rules_after),
                LOG_FIELD_OUTCOME: attempt.outcome,
            },
        )


def _escalate(read: GateRead, outcome: SlideFixOutcome) -> GateRead:
    failing = [slide.slide_index for slide in outcome.failing]
    _log(LOG_SLIDE_AUTOFIX_ESCALATED, read, {LOG_FIELD_FAILING_SLIDES: failing})
    decision = PolicyDecision(
        action=GateAction.ESCALATE,
        reason=read.decision.reason,
        detail=escalation_detail(outcome),
    )
    return GateRead(run=read.run, snapshot=read.snapshot, decision=decision)


class SlideAutofixStep:
    """At most one model fix per tick, between the repair and the decision."""

    def __init__(self, deps: SlideAutofixDependencies) -> None:
        self._deps = deps

    async def apply(self, read: GateRead) -> GateRead | None:
        """The gate to act on; None when the fix lost the lock (next tick).

        Returns ``read`` unchanged when no model fix applies, the gate read
        again when it is now clean (or fails for another reason), else an
        escalation that lists the slides still failing.
        """
        fixer = self._deps.fixer
        if fixer is None or not needs_model_fix(read):
            return read
        outcome = await fixer.fix_slides(
            SlideFixCommand(
                project_id=read.run.carousel_project_id or "",
                expected_version=read.snapshot.lock_version,
                phase=read.snapshot.phase,
            )
        )
        _log_attempts(read, outcome)
        if outcome.status is AutofixStatus.CONFLICT:
            _log(LOG_SLIDE_AUTOFIX_CONFLICT, read, {})
            return None
        fresh = (
            await self._reread(read) if outcome.status is AutofixStatus.FIXED else read
        )
        if not needs_model_fix(fresh):
            return fresh
        return _escalate(fresh, outcome)

    async def _reread(self, read: GateRead) -> GateRead:
        project_id = read.run.carousel_project_id or ""
        snapshot = await self._deps.editorial.read_gate(project_id)
        return GateRead(run=read.run, snapshot=snapshot, decision=decide(snapshot))


__all__ = [
    "SlideAutofixDependencies",
    "SlideAutofixStep",
    "escalation_detail",
    "needs_model_fix",
]
