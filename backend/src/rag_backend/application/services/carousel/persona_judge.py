"""The persona voice judge, retried once, never a fake verdict.

Prod be190a0c: on the same texts the fast-model judge answered ``overall``
0.0, then 7.8, then 78. A call that raises, times out, or parses to a 0 /
missing ``overall`` is a failed call, not a score: it is retried once, and a
second failure returns None (unscored) so no caller ever stores 0.0.

The judge's own timeout equals one queue model's timeout, so a
retry on the same queue never reached its next model (prod 8e484fe5: two
timeouts on the slow first model, then "unscored"). With a ``fallback``
judge (the same persona on the next model of the role's queue) the retry
goes to it.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

import structlog

from rag_backend.domain.constants.persona import (
    LOG_PERSONA_JUDGE_FAILED,
    PERSONA_JUDGE_CALLS,
    PERSONA_JUDGE_REASON_ERROR,
    PERSONA_JUDGE_REASON_NO_SCORE,
    PERSONA_JUDGE_TIMEOUT_SECONDS,
)
from rag_backend.domain.persona_score import stored_overall

logger = structlog.get_logger()


class VoiceJudge(Protocol):
    """``PersonaAgent.evaluate_match``: the scores of one text."""

    async def evaluate_match(self, content: str) -> dict[str, object]:
        """Raises on a transport or provider failure."""
        ...


async def _one_call(
    judge: VoiceJudge, text: str
) -> tuple[dict[str, object] | None, str]:
    """A provider or timeout failure is retried, not scored."""
    try:
        result = await asyncio.wait_for(
            judge.evaluate_match(text), timeout=PERSONA_JUDGE_TIMEOUT_SECONDS
        )
    except Exception as exc:
        return None, f"{PERSONA_JUDGE_REASON_ERROR}:{type(exc).__name__}"
    if stored_overall(result) is None:
        return None, PERSONA_JUDGE_REASON_NO_SCORE
    return result, ""


def _caller(judge: VoiceJudge, fallback: VoiceJudge | None, attempt: int) -> VoiceJudge:
    """The first call on ``judge``, the retry on ``fallback`` when set."""
    if attempt > 1 and fallback is not None:
        return fallback
    return judge


async def judge_voice(
    judge: VoiceJudge, text: str, fallback: VoiceJudge | None = None
) -> dict[str, object] | None:
    """The judge's scores of ``text``; None when two calls gave no score.

    The retry runs on ``fallback`` when one is given.
    """
    for attempt in range(1, PERSONA_JUDGE_CALLS + 1):
        caller = _caller(judge, fallback, attempt)
        result, reason = await _one_call(caller, text)
        if result is not None:
            return result
        logger.warning(
            LOG_PERSONA_JUDGE_FAILED,
            attempt=attempt,
            reason=reason,
            fallback=caller is not judge,
            unscored=attempt == PERSONA_JUDGE_CALLS,
        )
    return None


__all__ = ["VoiceJudge", "judge_voice"]
