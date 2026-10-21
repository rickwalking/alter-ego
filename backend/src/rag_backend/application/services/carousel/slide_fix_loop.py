"""The model fix of ONE failing slide, at most N attempts.

Each attempt sends the slide's current copy and every check it still fails;
the answer is read fence-aware, goes through the deterministic repair (the
same plan as the owner "Fix issues"), is validated against the whole deck,
and is voice-scored again only when its text changed. A model error, a
timeout or an unparseable answer counts as an attempt. The next attempt
starts from the last usable copy with the checks that copy still fails, so a
fix that breaks another rule is retried with the new violations.

After ``settings.attempts`` failed attempts on the fast model, up to
``settings.escalation_attempts`` more run on the reasoning model (numbered
on, 4 and 5). A judge that gives no score leaves the slide unscored: it keeps
its previous score and gets no voice issue. A field the model rewrote with a
correct sentence case loses its casing-repair marker.

An unscored slide is returned with ``unscored_ticks`` (its stored score
is stale), and on the next tick its current copy is re-scored before any
rewrite: a passing score fixes it as it is, a low one goes back to the
rewrite loop, and no score counts one more unscored tick.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, replace

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_paths import text_at
from rag_backend.application.services.carousel.owner_autofix_plan import plan_autofix
from rag_backend.application.services.carousel.slide_fix_casing import (
    MarkerClear,
    clear_rewritten_casing_markers,
)
from rag_backend.application.services.carousel.slide_fix_prompt import (
    apply_answer,
    render_slide_fix_prompt,
    slide_json,
)
from rag_backend.application.services.carousel.slide_fix_targets import slide_issues
from rag_backend.application.services.carousel.slide_fix_types import (
    DeckContext,
    FixAttempt,
    SlideFixResult,
    SlideFixSettings,
    SlideFixTools,
    SlideIssue,
    SlideRewriter,
    SlideTarget,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN
from rag_backend.domain.constants.slide_fix import (
    ATTEMPT_FIXED,
    ATTEMPT_MODEL_ERROR,
    ATTEMPT_STILL_FAILING,
    ATTEMPT_UNPARSEABLE,
    ISSUE_MODEL_ERROR,
    ISSUE_MODEL_UNPARSEABLE,
    ISSUE_VOICE_SCORE_LOW,
    ISSUE_VOICE_SCORE_MESSAGE,
    MODEL_ROLE_FAST,
    MODEL_ROLE_REASONING,
    SLIDE_FIX_TIMEOUT_SECONDS,
)
from rag_backend.domain.constants.workflow_state_fields import STATE_FIELD_SLIDE_INDEX

_HEADING = "heading"
_BODY = "body"
_MESSAGE_MODEL_ERROR = "The previous attempt failed: {error}. Try again."
_MESSAGE_UNPARSEABLE = (
    "The previous answer was not the JSON object asked for. Answer with the "
    "JSON object only."
)


@dataclass(frozen=True)
class LoopContext:
    """The deck, the injected model/scorer and the attempt budget."""

    deck: DeckContext
    tools: SlideFixTools
    settings: SlideFixSettings


@dataclass(frozen=True)
class _Stage:
    """One model and how many attempts it gets."""

    rewriter: SlideRewriter
    role: str
    attempts: int


@dataclass(frozen=True)
class _State:
    """``base_ticks`` counts the unscored ticks the slide had before this tick."""

    target: SlideTarget
    attempts: tuple[FixAttempt, ...] = ()
    feedback: tuple[SlideIssue, ...] = ()
    base_ticks: int = 0

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(issue.code for issue in self.target.issues))


def _score_text(record: Mapping[str, object]) -> str:
    payload = as_dict(record.get(PRESENTATION_PT_KEY)) or {}
    body = str(payload.get(_BODY) or "").strip()
    return body or str(payload.get(_HEADING) or "").strip()


def _voice_issue(score: float, floor: float) -> SlideIssue:
    message = ISSUE_VOICE_SCORE_MESSAGE.format(score=score, floor=floor)
    return SlideIssue(code=ISSUE_VOICE_SCORE_LOW, message=message)


def _with_slide(
    deck: DeckContext, record: dict[str, object]
) -> list[dict[str, object]]:
    index = record.get(STATE_FIELD_SLIDE_INDEX)
    return [
        record if item.get(STATE_FIELD_SLIDE_INDEX) == index else item
        for item in deck.records
    ]


def _copy_changed(before: Mapping[str, object], after: Mapping[str, object]) -> bool:
    return slide_json(before) != slide_json(after)


async def _rescore(
    candidate: dict[str, object], state: _State, ctx: LoopContext
) -> tuple[float | None, bool]:
    """The candidate's score and whether it was judged (False: unscored).

    Unchanged copy whose score is stale is still unjudged, and a missing score is not a
    verdict, so the previous one is kept.
    """
    scorer = ctx.tools.scorer
    if scorer is None or not ctx.deck.scored:
        return state.target.score, True
    if not _copy_changed(state.target.record, candidate):
        return state.target.score, state.target.unscored_ticks == 0
    score = await scorer.score(_score_text(candidate))
    return (state.target.score, False) if score is None else (score, True)


async def _evaluate(
    candidate: dict[str, object], state: _State, ctx: LoopContext
) -> SlideTarget:
    repaired = plan_autofix([candidate], ctx.deck.autofix).records[0]
    deck = _with_slide(ctx.deck, repaired)
    issues = slide_issues(deck, ctx.deck.policy_version).get(
        state.target.slide_index, []
    )
    score, judged = await _rescore(repaired, state, ctx)
    if judged and score is not None and score < ctx.settings.voice_floor:
        issues.append(_voice_issue(score, ctx.settings.voice_floor))
    ticks = 0 if judged else state.base_ticks + 1
    return replace(
        state.target,
        record=repaired,
        issues=tuple(issues),
        score=score,
        unscored_ticks=ticks,
    )


def _attempt(
    state: _State, role: str, result: tuple[tuple[str, ...], str]
) -> FixAttempt:
    after, outcome = result
    return FixAttempt(
        slide_index=state.target.slide_index,
        attempt=len(state.attempts) + 1,
        rules_before=state.codes,
        rules_after=after,
        outcome=outcome,
        model_role=role,
    )


def _failed(state: _State, role: str, failure: tuple[str, SlideIssue]) -> _State:
    outcome, feedback = failure
    attempt = _attempt(state, role, (state.codes, outcome))
    return replace(state, attempts=(*state.attempts, attempt), feedback=(feedback,))


async def _candidate(
    state: _State, ctx: LoopContext, stage: _Stage
) -> dict[str, object] | None:
    guide = (ctx.deck.autofix.policy, ctx.tools.style_guide, ctx.settings.voice_floor)
    issues = (*state.target.issues, *state.feedback)
    prompt = render_slide_fix_prompt(state.target, issues, guide)
    answer = await asyncio.wait_for(
        stage.rewriter.rewrite(prompt), timeout=SLIDE_FIX_TIMEOUT_SECONDS
    )
    candidate = apply_answer(state.target.record, answer)
    if candidate is None:
        return None
    clear = MarkerClear(answer=answer, policy=ctx.deck.autofix.policy)
    return clear_rewritten_casing_markers(candidate, clear)


async def _one_attempt(state: _State, ctx: LoopContext, stage: _Stage) -> _State:
    """A provider, timeout or scorer failure counts as an attempt."""
    try:
        candidate = await _candidate(state, ctx, stage)
        if candidate is None:
            unusable = SlideIssue(
                code=ISSUE_MODEL_UNPARSEABLE, message=_MESSAGE_UNPARSEABLE
            )
            return _failed(state, stage.role, (ATTEMPT_UNPARSEABLE, unusable))
        evaluated = await _evaluate(candidate, state, ctx)
    except Exception as exc:
        message = _MESSAGE_MODEL_ERROR.format(error=type(exc).__name__)
        error = SlideIssue(code=ISSUE_MODEL_ERROR, message=message)
        return _failed(state, stage.role, (ATTEMPT_MODEL_ERROR, error))
    after = tuple(dict.fromkeys(issue.code for issue in evaluated.issues))
    outcome = ATTEMPT_STILL_FAILING if evaluated.issues else ATTEMPT_FIXED
    attempt = _attempt(state, stage.role, (after, outcome))
    attempts = (*state.attempts, attempt)
    return replace(state, target=evaluated, attempts=attempts, feedback=())


def _stages(ctx: LoopContext) -> tuple[_Stage, ...]:
    """The fast model, then the reasoning model when one is wired."""
    fast = _Stage(ctx.tools.rewriter, MODEL_ROLE_FAST, max(1, ctx.settings.attempts))
    stronger = ctx.tools.escalation_rewriter
    if stronger is None or ctx.settings.escalation_attempts <= 0:
        return (fast,)
    escalation = _Stage(
        stronger, MODEL_ROLE_REASONING, ctx.settings.escalation_attempts
    )
    return (fast, escalation)


async def _judge_stale(target: SlideTarget, ctx: LoopContext) -> float | None:
    """A scorer failure is no score, as in ``judge_voice``."""
    scorer = ctx.tools.scorer
    if scorer is None:
        return None
    try:
        return await scorer.score(_score_text(target.record))
    except Exception:
        return None


async def _rescore_stale(target: SlideTarget, ctx: LoopContext) -> SlideTarget:
    """Re-score a stale slide's current copy before any rewrite."""
    if target.unscored_ticks == 0:
        return target
    score = await _judge_stale(target, ctx)
    floor = ctx.settings.voice_floor
    rules = tuple(
        issue for issue in target.issues if issue.code != ISSUE_VOICE_SCORE_LOW
    )
    if score is None:
        return replace(target, issues=rules, unscored_ticks=target.unscored_ticks + 1)
    issues = rules if score >= floor else (*rules, _voice_issue(score, floor))
    return replace(target, issues=issues, score=score, unscored_ticks=0)


def _fixed(state: _State) -> SlideFixResult:
    """A slide that never had a score has no stale score to re-score."""
    stale = state.target.score is not None
    return SlideFixResult(
        slide_index=state.target.slide_index,
        fixed=True,
        record=state.target.record,
        issues=(),
        attempts=state.attempts,
        score=state.target.score,
        unscored_ticks=state.target.unscored_ticks if stale else 0,
    )


async def fix_slide(target: SlideTarget, ctx: LoopContext) -> SlideFixResult:
    """Rewrite one slide until it passes, on the fast then the reasoning model."""
    rescored = await _rescore_stale(target, ctx)
    state = _State(target=rescored, base_ticks=target.unscored_ticks)
    if not rescored.issues:
        return _fixed(state)
    rounds = [stage for stage in _stages(ctx) for _ in range(stage.attempts)]
    for stage in rounds:
        state = await _one_attempt(state, ctx, stage)
        if state.attempts[-1].outcome == ATTEMPT_FIXED:
            return _fixed(state)
    return SlideFixResult(
        slide_index=target.slide_index,
        fixed=False,
        record=target.record,
        issues=state.target.issues,
        attempts=state.attempts,
        score=target.score,
    )


def current_text(result: SlideFixResult) -> str:
    """The text of the first failing field, else the PT body (for the owner)."""
    for issue in result.issues:
        key = (
            PRESENTATION_PT_KEY if issue.locale != LANGUAGE_EN else PRESENTATION_EN_KEY
        )
        payload = as_dict(result.record.get(key)) or {}
        text = text_at(payload, issue.field) if issue.field else ""
        if text.strip():
            return text.strip()
    return _score_text(result.record)


__all__ = ["LoopContext", "current_text", "fix_slide"]
