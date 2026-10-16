"""The model fix of ONE failing slide, at most N attempts (AE-0401).

Each attempt sends the slide's current copy and every check it still fails;
the answer is read fence-aware, goes through the deterministic repair (the
same plan as the owner "Fix issues"), is validated against the whole deck,
and is voice-scored again only when its text changed. A model error, a
timeout or an unparseable answer counts as an attempt. The next attempt
starts from the last usable copy with the checks that copy still fails, so a
fix that breaks another rule is retried with the new violations.
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
class _State:
    target: SlideTarget
    attempts: tuple[FixAttempt, ...] = ()
    feedback: tuple[SlideIssue, ...] = ()

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
) -> float | None:
    scorer = ctx.tools.scorer
    if scorer is None or not ctx.deck.scored:
        return state.target.score
    if not _copy_changed(state.target.record, candidate):
        return state.target.score
    return await scorer.score(_score_text(candidate))


async def _evaluate(
    candidate: dict[str, object], state: _State, ctx: LoopContext
) -> SlideTarget:
    repaired = plan_autofix([candidate], ctx.deck.autofix).records[0]
    deck = _with_slide(ctx.deck, repaired)
    issues = slide_issues(deck, ctx.deck.policy_version).get(
        state.target.slide_index, []
    )
    score = await _rescore(repaired, state, ctx)
    if score is not None and score < ctx.settings.voice_floor:
        issues.append(_voice_issue(score, ctx.settings.voice_floor))
    return replace(state.target, record=repaired, issues=tuple(issues), score=score)


def _attempt(state: _State, after: tuple[str, ...], outcome: str) -> FixAttempt:
    return FixAttempt(
        slide_index=state.target.slide_index,
        attempt=len(state.attempts) + 1,
        rules_before=state.codes,
        rules_after=after,
        outcome=outcome,
    )


def _failed(state: _State, outcome: str, feedback: SlideIssue) -> _State:
    attempt = _attempt(state, state.codes, outcome)
    return replace(state, attempts=(*state.attempts, attempt), feedback=(feedback,))


async def _one_attempt(state: _State, ctx: LoopContext) -> _State:
    guide = (ctx.deck.autofix.policy, ctx.tools.style_guide, ctx.settings.voice_floor)
    issues = (*state.target.issues, *state.feedback)
    prompt = render_slide_fix_prompt(state.target, issues, guide)
    try:
        answer = await asyncio.wait_for(
            ctx.tools.rewriter.rewrite(prompt), timeout=SLIDE_FIX_TIMEOUT_SECONDS
        )
        candidate = apply_answer(state.target.record, answer)
        if candidate is None:
            unusable = SlideIssue(
                code=ISSUE_MODEL_UNPARSEABLE, message=_MESSAGE_UNPARSEABLE
            )
            return _failed(state, ATTEMPT_UNPARSEABLE, unusable)
        evaluated = await _evaluate(candidate, state, ctx)
    except Exception as exc:  # a provider/timeout/scorer failure counts as an attempt
        message = _MESSAGE_MODEL_ERROR.format(error=type(exc).__name__)
        return _failed(
            state,
            ATTEMPT_MODEL_ERROR,
            SlideIssue(code=ISSUE_MODEL_ERROR, message=message),
        )
    after = tuple(dict.fromkeys(issue.code for issue in evaluated.issues))
    outcome = ATTEMPT_STILL_FAILING if evaluated.issues else ATTEMPT_FIXED
    attempt = _attempt(state, after, outcome)
    return _State(target=evaluated, attempts=(*state.attempts, attempt))


async def fix_slide(target: SlideTarget, ctx: LoopContext) -> SlideFixResult:
    """Rewrite one slide until it passes, at most ``settings.attempts`` times."""
    state = _State(target=target)
    for _ in range(max(1, ctx.settings.attempts)):
        state = await _one_attempt(state, ctx)
        if state.attempts[-1].outcome == ATTEMPT_FIXED:
            return SlideFixResult(
                slide_index=target.slide_index,
                fixed=True,
                record=state.target.record,
                issues=(),
                attempts=state.attempts,
                score=state.target.score,
            )
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
