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

from rag_backend.modules.generation_queue.application.generation_events import (
    NO_EVENT_RECORDER,
    NO_RUN_COMPLETION,
    current_generation_event_project,
    generation_event_run,
    generation_event_scope,
    record_generation_event,
)
from rag_backend.modules.generation_queue.application.job_tracker import (
    _Attempt,
    _StaleAttemptError,
    _Tracker,
)
from rag_backend.modules.generation_queue.constants import (
    ERROR_MESSAGE_MAX_CHARS,
    ERROR_UNKNOWN_KIND,
    EVENT_RUN_DEAD_LETTER,
    EVENT_RUN_RETRY,
    EVENT_RUN_STARTED,
    EVENT_RUN_SUCCEEDED,
    EVENT_RUN_WAITING,
    LOCK_BUSY_DELAY_SECONDS,
    LOG_DEAD_LETTER,
    LOG_LOCK_BUSY,
    LOG_RETRY,
    LOG_STARTED,
    LOG_SUCCEEDED,
    MESSAGE_GENERATION_FAILED,
    MESSAGE_GENERATION_RETRY,
    MESSAGE_GENERATION_STARTED,
    MESSAGE_GENERATION_SUCCEEDED,
    MESSAGE_GENERATION_WAITING,
    OUTCOME_DEAD_LETTER,
    OUTCOME_RETRY_WAIT,
    OUTCOME_RUNNING,
    OUTCOME_SUCCEEDED,
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
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRecorder,
    GenerationRunCompletion,
)
from rag_backend.modules.generation_queue.domain.models import (
    AttemptDeadLetterCommand,
    GenerationKind,
    GenerationRun,
    GenerationStatus,
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
WAIT_STREAK_CODES = frozenset({LOCK_BUSY_CODE, WAITING_CODE})


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
    error_type: str | None = None


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
    events: GenerationEventRecorder = NO_EVENT_RECORDER
    completion: GenerationRunCompletion = NO_RUN_COMPLETION


class GenerationJobHandler:
    """Load the run, take the drive lock, run its executor, record the outcome."""

    def __init__(self, deps: HandlerDependencies) -> None:
        self._deps = deps

    async def handle(self, run_id: UUID) -> Verdict:
        """Process the generation run ``run_id`` carried by a PgQueuer job."""
        run = await self._deps.store.get(run_id)
        if run is None or not is_active(run.status):
            return _DONE
        async with generation_event_scope(generation_event_run(run), self._deps.events):
            return await self._handle_active(run)

    async def _handle_active(self, run: GenerationRun) -> Verdict:
        attempt_id = await self._deps.store.mark_running(run.id)
        if attempt_id is None:
            return _DONE
        attempt = _Attempt(
            run=run, attempt_id=attempt_id, started_at=self._deps.clock.now()
        )
        executor = self._deps.executors.get(run.kind)
        if executor is None:
            return await self._dead(
                attempt, PermanentGenerationError(ERROR_UNKNOWN_KIND)
            )
        return await self._run(attempt, executor)

    async def _run(self, attempt: _Attempt, executor: KindExecutor) -> Verdict:
        tracker = _Tracker(self._deps, attempt, lambda: _record_started(attempt))
        try:
            async with self._deps.lock.hold(await executor.lock_keys(attempt.run)):
                outcome = await executor.execute(attempt.run, tracker)
        except DriveLockBusyError:
            logger.info(LOG_LOCK_BUSY, generation_run_id=str(attempt.run.id))
            return await self._retry(
                attempt, _RetryPlan(LOCK_BUSY_CODE, LOCK_BUSY_DELAY)
            )
        except BudgetExhaustedError as exc:
            return await self._dead(attempt, exc, tracker)
        except _StaleAttemptError:
            return _DONE
        except Exception as exc:
            return await self._failed(attempt, exc, tracker)
        return await self._settle(attempt, outcome, tracker)

    async def _settle(
        self, attempt: _Attempt, outcome: StepOutcome, tracker: _Tracker
    ) -> Verdict:
        delay = _OUTCOME_DELAYS.get(outcome)
        if outcome is StepOutcome.WAIT and delay is not None:
            return await self._retry(attempt, _RetryPlan(WAITING_CODE, delay))
        if delay is not None:
            await tracker.ensure_started()
            return await self._retry(attempt, _RetryPlan(WAITING_CODE, delay))
        await tracker.ensure_started()
        moved = await self._deps.store.mark_succeeded(
            attempt.run.id, attempt.attempt_id
        )
        if not moved:
            return _DONE
        logger.info(LOG_SUCCEEDED, generation_run_id=str(attempt.run.id))
        await record_generation_event(
            GenerationEventInput(
                event_type=EVENT_RUN_SUCCEEDED,
                outcome=OUTCOME_SUCCEEDED,
                occurred_at=self._deps.clock.now(),
                message_code=MESSAGE_GENERATION_SUCCEEDED,
            )
        )
        project_id = current_generation_event_project()
        if project_id is not None:
            await self._deps.completion.completed(project_id, succeeded=True)
        return _DONE

    async def _retry(
        self, attempt: _Attempt, plan: _RetryPlan, tracker: _Tracker | None = None
    ) -> Verdict:
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
        if tracker is not None:
            await tracker.fail(plan.code)
        if plan.code in WAIT_STREAK_CODES:
            await self._record_wait(attempt, plan)
            return Verdict(VerdictKind.RETRY, plan.delay)
        await record_generation_event(
            GenerationEventInput(
                event_type=EVENT_RUN_RETRY,
                outcome=OUTCOME_RETRY_WAIT,
                occurred_at=self._deps.clock.now(),
                error_code=plan.code,
                message_code=MESSAGE_GENERATION_RETRY,
                details=_retry_details(plan),
            )
        )
        return Verdict(VerdictKind.RETRY, plan.delay)

    async def _record_wait(self, attempt: _Attempt, plan: _RetryPlan) -> None:
        if _in_wait_streak(attempt.run):
            return
        await record_generation_event(
            GenerationEventInput(
                event_type=EVENT_RUN_WAITING,
                outcome=OUTCOME_RETRY_WAIT,
                occurred_at=self._deps.clock.now(),
                error_code=plan.code,
                message_code=MESSAGE_GENERATION_WAITING,
                details=_retry_details(plan),
            )
        )

    async def _failed(
        self, attempt: _Attempt, exc: Exception, tracker: _Tracker
    ) -> Verdict:
        await tracker.ensure_started()
        failure = classify(exc, self._deps.is_provider_error)
        if failure is FailureClass.PERMANENT:
            return await self._dead(attempt, exc, tracker)
        delay = budget.retry_delay(tracker.counts.attempts, self._deps.uniform)
        logger.warning(
            LOG_RETRY,
            generation_run_id=str(attempt.run.id),
            error_type=type(exc).__name__,
            delay_seconds=round(delay.total_seconds()),
        )
        plan = _RetryPlan(
            failure.value,
            delay,
            _describe(exc),
            error_type=type(exc).__name__,
        )
        return await self._retry(attempt, plan, tracker)

    async def _dead(
        self, attempt: _Attempt, exc: Exception, tracker: _Tracker | None = None
    ) -> Verdict:
        if tracker is None:
            await _record_started(attempt)
        else:
            await tracker.ensure_started()
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
        if tracker is not None:
            await tracker.fail(code)
        await self._deps.notices.stage(attempt.run, code)
        await record_generation_event(
            GenerationEventInput(
                event_type=EVENT_RUN_DEAD_LETTER,
                outcome=OUTCOME_DEAD_LETTER,
                occurred_at=self._deps.clock.now(),
                error_code=code,
                message_code=MESSAGE_GENERATION_FAILED,
                details={"error_type": type(exc).__name__},
            )
        )
        logger.warning(
            LOG_DEAD_LETTER, generation_run_id=str(attempt.run.id), error_code=code
        )
        project_id = current_generation_event_project()
        if project_id is not None:
            await self._deps.completion.completed(project_id, succeeded=False)
        return _HOLD


async def _record_started(attempt: _Attempt) -> None:
    run = attempt.run
    logger.info(LOG_STARTED, generation_run_id=str(run.id), kind=run.kind.value)
    await record_generation_event(
        GenerationEventInput(
            event_type=EVENT_RUN_STARTED,
            outcome=OUTCOME_RUNNING,
            occurred_at=attempt.started_at,
            attempt=run.attempts + 1,
            message_code=MESSAGE_GENERATION_STARTED,
            details={"resumed": True} if _in_wait_streak(run) else {},
        )
    )


def _in_wait_streak(run: GenerationRun) -> bool:
    return (
        run.status is GenerationStatus.RETRY_WAIT
        and run.last_error_code in WAIT_STREAK_CODES
    )


def _retry_details(plan: _RetryPlan) -> dict[str, object]:
    details: dict[str, object] = {"delay_seconds": round(plan.delay.total_seconds())}
    if plan.error_type is not None:
        details["error_type"] = plan.error_type
    return details


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
