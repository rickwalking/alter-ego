"""Run one generation job and decide what PgQueuer does with it.

The handler never imports PgQueuer: it returns a ``Verdict`` (done, retry after a
delay, hold) and the worker adapter turns it into PgQueuer's own signals. Every
state change is written to ``generation_runs`` before the verdict is returned, so
the dashboard and Telegram never depend on PgQueuer's tables.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from uuid import UUID

import structlog

from rag_backend.modules.generation_queue.constants import (
    ERROR_MESSAGE_MAX_CHARS,
    ERROR_UNKNOWN_KIND,
    LOCK_BUSY_DELAY_SECONDS,
    LOG_DEAD_LETTER,
    LOG_LOCK_BUSY,
    LOG_RETRY,
    LOG_STARTED,
    LOG_SUCCEEDED,
    RESTART_DELAY_SECONDS,
    WAIT_DELAY_SECONDS,
)
from rag_backend.modules.generation_queue.domain import budget
from rag_backend.modules.generation_queue.domain.errors import (
    BudgetExhaustedError,
    DriveLockBusyError,
    FailureClass,
    PermanentGenerationError,
    ProviderClassifier,
    classify,
)
from rag_backend.modules.generation_queue.domain.models import (
    AttemptDeadLetterCommand,
    CountsUpdate,
    GenerationKind,
    GenerationRun,
    RetryCommand,
    is_active,
)
from rag_backend.modules.generation_queue.domain.ports import (
    Clock,
    DeadLetterNotices,
    DriveLock,
    GenerationRunStore,
    KindExecutor,
    StepOutcome,
)

logger = structlog.get_logger()

Uniform = Callable[[float, float], float]
_SYSTEM_RANDOM = random.SystemRandom()

LOCK_BUSY_CODE = "drive_lock_busy"
WAITING_CODE = "waiting"


class VerdictKind(StrEnum):
    """What PgQueuer should do with the job."""

    DONE = "done"
    RETRY = "retry"
    HOLD = "hold"


@dataclass(frozen=True)
class Verdict:
    """The handler's answer for one job."""

    kind: VerdictKind
    delay: timedelta = timedelta(0)


_DONE = Verdict(VerdictKind.DONE)
_HOLD = Verdict(VerdictKind.HOLD)
_OUTCOME_DELAYS: dict[StepOutcome, timedelta] = {
    StepOutcome.WAIT: timedelta(seconds=WAIT_DELAY_SECONDS),
    StepOutcome.YIELD: timedelta(seconds=RESTART_DELAY_SECONDS),
}
LOCK_BUSY_DELAY = timedelta(seconds=LOCK_BUSY_DELAY_SECONDS)


@dataclass(frozen=True)
class _RetryPlan:
    """Why and when the job comes back."""

    code: str
    delay: timedelta
    error: str = ""


@dataclass(frozen=True, kw_only=True)
class HandlerDependencies:
    """Collaborators of the job handler."""

    store: GenerationRunStore
    lock: DriveLock
    executors: Mapping[GenerationKind, KindExecutor]
    notices: DeadLetterNotices
    clock: Clock
    is_provider_error: ProviderClassifier
    uniform: Uniform = _SYSTEM_RANDOM.uniform
    budget: budget.AttemptBudget = field(default_factory=budget.AttemptBudget)


@dataclass(frozen=True)
class _Attempt:
    """The run snapshot and UUID claimed by one handler invocation."""

    run: GenerationRun
    attempt_id: UUID


class _StaleAttemptError(Exception):
    """The attempt lost its fence while its executor was running."""


class _Tracker:
    """Counts phase starts for one job, persisting before the work runs."""

    def __init__(self, deps: HandlerDependencies, attempt: _Attempt) -> None:
        self._deps = deps
        self._run_id = attempt.run.id
        self._attempt_id = attempt.attempt_id
        self.counts = attempt.run.counts

    async def begin(self, phase: str) -> None:
        self.counts = budget.begin(self.counts, phase)
        await self._save(phase)
        error_code = budget.exhausted(self.counts, phase, self._deps.budget)
        if error_code is not None:
            raise BudgetExhaustedError(error_code)

    async def finish(self, phase: str) -> None:
        self.counts = budget.finish(self.counts, phase)
        await self._save(phase)

    async def _save(self, phase: str) -> None:
        update = CountsUpdate(counts=self.counts, phase=phase)
        saved = await self._deps.store.save_counts(
            self._run_id, self._attempt_id, update
        )
        if not saved:
            raise _StaleAttemptError


class GenerationJobHandler:
    """Load the run, take the drive lock, run its executor, record the outcome."""

    def __init__(self, deps: HandlerDependencies) -> None:
        self._deps = deps

    async def handle(self, run_id: UUID) -> Verdict:
        """Process the generation run ``run_id`` carried by a PgQueuer job."""
        run = await self._deps.store.get(run_id)
        if run is None or not is_active(run.status):
            return _DONE
        attempt_id = await self._deps.store.mark_running(run.id)
        if attempt_id is None:
            return _DONE
        attempt = _Attempt(run=run, attempt_id=attempt_id)
        executor = self._deps.executors.get(run.kind)
        if executor is None:
            return await self._dead(
                attempt, PermanentGenerationError(ERROR_UNKNOWN_KIND)
            )
        logger.info(LOG_STARTED, generation_run_id=str(run.id), kind=run.kind.value)
        return await self._run(attempt, executor)

    async def _run(self, attempt: _Attempt, executor: KindExecutor) -> Verdict:
        run = attempt.run
        tracker = _Tracker(self._deps, attempt)
        try:
            async with self._deps.lock.hold(await executor.lock_keys(run)):
                outcome = await executor.execute(run, tracker)
        except DriveLockBusyError:
            logger.info(LOG_LOCK_BUSY, generation_run_id=str(run.id))
            return await self._retry(
                attempt, _RetryPlan(LOCK_BUSY_CODE, LOCK_BUSY_DELAY)
            )
        except BudgetExhaustedError as exc:
            return await self._dead(attempt, exc)
        except _StaleAttemptError:
            return _DONE
        except Exception as exc:
            return await self._failed(attempt, exc, tracker.counts.attempts)
        return await self._settle(attempt, outcome)

    async def _settle(self, attempt: _Attempt, outcome: StepOutcome) -> Verdict:
        delay = _OUTCOME_DELAYS.get(outcome)
        if delay is not None:
            return await self._retry(attempt, _RetryPlan(WAITING_CODE, delay))
        moved = await self._deps.store.mark_succeeded(
            attempt.run.id, attempt.attempt_id
        )
        if not moved:
            return _DONE
        logger.info(LOG_SUCCEEDED, generation_run_id=str(attempt.run.id))
        return _DONE

    async def _retry(self, attempt: _Attempt, plan: _RetryPlan) -> Verdict:
        moved = await self._deps.store.mark_waiting(
            RetryCommand(
                run_id=attempt.run.id,
                attempt_id=attempt.attempt_id,
                next_attempt_at=self._deps.clock.now() + plan.delay,
                error_code=plan.code,
                error=plan.error[:ERROR_MESSAGE_MAX_CHARS],
            )
        )
        if not moved:
            return _DONE
        return Verdict(VerdictKind.RETRY, plan.delay)

    async def _failed(
        self, attempt: _Attempt, exc: Exception, attempts: int
    ) -> Verdict:
        failure = classify(exc, self._deps.is_provider_error)
        if failure is FailureClass.PERMANENT:
            return await self._dead(attempt, exc)
        delay = budget.retry_delay(attempts, self._deps.uniform)
        logger.warning(
            LOG_RETRY,
            generation_run_id=str(attempt.run.id),
            error_type=type(exc).__name__,
            delay_seconds=round(delay.total_seconds()),
        )
        plan = _RetryPlan(failure.value, delay, _describe(exc))
        return await self._retry(attempt, plan)

    async def _dead(self, attempt: _Attempt, exc: Exception) -> Verdict:
        code = _error_code(exc)
        command = AttemptDeadLetterCommand(
            run_id=attempt.run.id,
            attempt_id=attempt.attempt_id,
            error_code=code,
            error=_describe(exc)[:ERROR_MESSAGE_MAX_CHARS],
        )
        moved = await self._deps.store.mark_attempt_dead_letter(command)
        if not moved:
            return _DONE
        await self._deps.notices.stage(attempt.run, code)
        logger.warning(
            LOG_DEAD_LETTER, generation_run_id=str(attempt.run.id), error_code=code
        )
        return _HOLD


def _error_code(exc: Exception) -> str:
    """The classified code of a failure that parks the run."""
    if isinstance(exc, BudgetExhaustedError | PermanentGenerationError):
        return exc.error_code
    return FailureClass.PERMANENT.value


def _describe(exc: BaseException) -> str:
    """Exception type and message, no traceback (no secrets in the row)."""
    return f"{type(exc).__name__}: {exc}"


__all__ = [
    "GenerationJobHandler",
    "HandlerDependencies",
    "Verdict",
    "VerdictKind",
]
