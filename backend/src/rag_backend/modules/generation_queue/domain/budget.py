"""Attempt budgets and retry delays of the generation queue.

Our counters are authoritative: PgQueuer does not count a stale-heartbeat re-pick
as an attempt, so a worker that keeps dying on the same phase (OOM, crash loop)
would otherwise be re-run forever. A start is counted before the work runs and
taken back when the phase finishes cleanly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from rag_backend.modules.generation_queue.constants import (
    ERROR_PHASE_BUDGET,
    ERROR_RUN_BUDGET,
    MAX_PHASE_ATTEMPTS,
    MAX_RUN_ATTEMPTS,
    RETRY_INITIAL_SECONDS,
    RETRY_JITTER,
    RETRY_MAX_SECONDS,
    RETRY_MULTIPLIER,
)


@dataclass(frozen=True)
class AttemptCounts:
    """The run-level and per-phase counters of one generation run."""

    attempts: int
    phase_attempts: dict[str, int]


@dataclass(frozen=True)
class AttemptBudget:
    """How many unfinished starts a phase and a run may have."""

    max_phase: int = MAX_PHASE_ATTEMPTS
    max_run: int = MAX_RUN_ATTEMPTS


def begin(counts: AttemptCounts, phase: str) -> AttemptCounts:
    """Count a start of ``phase`` (before any work runs)."""
    phases = dict(counts.phase_attempts)
    phases[phase] = phases.get(phase, 0) + 1
    return AttemptCounts(attempts=counts.attempts + 1, phase_attempts=phases)


def finish(counts: AttemptCounts, phase: str) -> AttemptCounts:
    """Take back the start of ``phase``: it finished, so it made progress."""
    phases = dict(counts.phase_attempts)
    if phases.pop(phase, 0) == 0:
        return counts
    return AttemptCounts(attempts=max(counts.attempts - 1, 0), phase_attempts=phases)


def exhausted(counts: AttemptCounts, phase: str, budget: AttemptBudget) -> str | None:
    """The budget error code once a start would exceed a budget, else None."""
    if counts.phase_attempts.get(phase, 0) > budget.max_phase:
        return ERROR_PHASE_BUDGET
    if counts.attempts > budget.max_run:
        return ERROR_RUN_BUDGET
    return None


def reset_phase(counts: AttemptCounts, phase: str | None) -> AttemptCounts:
    """Forget the failing phase's starts on a retry ("Tentar de novo")."""
    if phase is None:
        return counts
    phases = dict(counts.phase_attempts)
    dropped = phases.pop(phase, 0)
    return AttemptCounts(
        attempts=max(counts.attempts - dropped, 0), phase_attempts=phases
    )


def retry_delay(attempt: int, uniform: Callable[[float, float], float]) -> timedelta:
    """Exponential backoff from 30 s doubling to 30 min, with ±20 % jitter."""
    exponent = max(attempt - 1, 0)
    base = min(RETRY_INITIAL_SECONDS * RETRY_MULTIPLIER**exponent, RETRY_MAX_SECONDS)
    factor = uniform(1 - RETRY_JITTER, 1 + RETRY_JITTER)
    return timedelta(seconds=base * factor)


__all__ = [
    "AttemptBudget",
    "AttemptCounts",
    "begin",
    "exhausted",
    "finish",
    "reset_phase",
    "retry_delay",
]
