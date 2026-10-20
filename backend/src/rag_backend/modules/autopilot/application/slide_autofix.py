"""Model fix of failing slides after the deterministic repair (AE-0401).

Autopilot only, at the content and design gates. A gate that still fails on
content quality (blocking presentation rules) or on a low voice score after
the AE-0392 repair is not revised: each failing slide is rewritten by the
fast model, at most ``AUTOPILOT_AUTOFIX_ATTEMPTS`` times, then by the
reasoning model at most ``AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS`` times
(AE-0407, attempts numbered on), the fixed slides are
written through the editorial facade, and the gate is read again. A clean
gate is approved; otherwise the run escalates to the owner with every slide
the fix gave up on. The revise budget is never spent on these reasons; other
reasons (research, outline, images, forbidden phrases) keep revise/escalate.

AE-0433: a fixed slide the persona judge could not score keeps its old
(stale) voice score, so the gate read again can still fail on the voice
floor with no slide failing. That is not "below threshold": the run waits
(stays generating) for the re-score on the next tick and, once a slide
stayed unscored for the configured ticks, escalates
``persona_judge_unavailable``.
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
    ESCALATION_SLIDE_SEPARATOR,
    ESCALATION_TEXT_ELLIPSIS,
    ESCALATION_TEXT_MAX_CHARS,
    ESCALATION_UNSCORED_LINE,
    LOG_FIELD_ATTEMPT,
    LOG_FIELD_FAILING_SLIDES,
    LOG_FIELD_JUDGE_UNAVAILABLE,
    LOG_FIELD_MODEL_ROLE,
    LOG_FIELD_OUTCOME,
    LOG_FIELD_RULES_AFTER,
    LOG_FIELD_RULES_BEFORE,
    LOG_FIELD_SLIDE,
    LOG_FIELD_UNSCORED_SLIDES,
    LOG_SLIDE_AUTOFIX,
    LOG_SLIDE_AUTOFIX_CONFLICT,
    LOG_SLIDE_AUTOFIX_ESCALATED,
    LOG_SLIDE_AUTOFIX_UNSCORED,
    REASON_PERSONA_JUDGE_UNAVAILABLE,
    REASON_PERSONA_RESCORE_PENDING,
)
from rag_backend.modules.autopilot.constants import REASON_PERSONA_SCORE
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
                LOG_FIELD_MODEL_ROLE: attempt.model_role,
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


def _judge_pending(read: GateRead, outcome: SlideFixOutcome) -> bool:
    """Only the stale voice scores hold the gate: wait for the re-score.

    AE-0433: the gate fails on the voice floor, no slide is still failing
    and no rule is unfixable. AE-0439 (#154 B/C): the gate may already PASS
    on a stale score (the read path ignores the pending marker) — the run
    still waits, and never approves on the stale score; and the wait fires
    only when the persona reason is the SOLE failure: a forbidden hit, a
    blocking quality rule or an engine refusal alongside it escalates
    instead of waiting forever.
    """
    if not outcome.unscored_slides or outcome.failing or outcome.unfixable_rules:
        return False
    if read.decision.action is GateAction.APPROVE:
        return True
    return (
        read.decision.reason == REASON_PERSONA_SCORE
        and not read.snapshot.forbidden_hits
        and not read.snapshot.quality_violations
        and not read.snapshot.engine_blocker
    )


def _unscored(read: GateRead, outcome: SlideFixOutcome) -> GateRead:
    """Wait for the re-score, or escalate once the judge stayed down (AE-0433)."""
    slides = list(outcome.unscored_slides)
    extra = {
        LOG_FIELD_UNSCORED_SLIDES: slides,
        LOG_FIELD_JUDGE_UNAVAILABLE: outcome.judge_unavailable,
    }
    _log(LOG_SLIDE_AUTOFIX_UNSCORED, read, extra)
    if not outcome.judge_unavailable:
        decision = PolicyDecision(
            action=GateAction.WAIT, reason=REASON_PERSONA_RESCORE_PENDING
        )
        return GateRead(run=read.run, snapshot=read.snapshot, decision=decision)
    joined = ESCALATION_SLIDE_SEPARATOR.join(str(slide) for slide in slides)
    decision = PolicyDecision(
        action=GateAction.ESCALATE,
        reason=REASON_PERSONA_JUDGE_UNAVAILABLE,
        detail=ESCALATION_UNSCORED_LINE.format(slides=joined),
    )
    return GateRead(run=read.run, snapshot=read.snapshot, decision=decision)


class SlideAutofixStep:
    """At most one model fix per tick, between the repair and the decision."""

    def __init__(self, deps: SlideAutofixDependencies) -> None:
        self._deps = deps

    async def apply(self, read: GateRead) -> GateRead | None:
        """The gate to act on; None when the fix lost the lock (next tick).

        Returns ``read`` unchanged when no model fix applies, the gate read
        again when it is now clean (or fails for another reason), a wait or
        a ``persona_judge_unavailable`` escalation when only unscored slides
        hold it (AE-0433), else an escalation that lists the slides still
        failing. AE-0439 (#154 B): pending re-scores are fixed even when the
        gate PASSES on their stale scores, so a stale score is never
        approved and the markers clear once the judge scores again.
        """
        fixer = self._deps.fixer
        if fixer is None or (
            not needs_model_fix(read) and not read.snapshot.pending_rescores
        ):
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
        if _judge_pending(fresh, outcome):
            return _unscored(fresh, outcome)
        if needs_model_fix(fresh):
            return _escalate(fresh, outcome)
        return fresh

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
