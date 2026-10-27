"""Fenced phase-attempt counting and generation-event timing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from rag_backend.modules.generation_queue.application.generation_events import (
    record_generation_event,
)
from rag_backend.modules.generation_queue.constants import (
    EVENT_PHASE_FAILED,
    EVENT_PHASE_STARTED,
    EVENT_PHASE_SUCCEEDED,
    MESSAGE_PHASE_FAILED,
    MESSAGE_PHASE_STARTED,
    MESSAGE_PHASE_SUCCEEDED,
    OUTCOME_FAILED,
    OUTCOME_RUNNING,
    OUTCOME_SUCCEEDED,
)
from rag_backend.modules.generation_queue.domain import budget
from rag_backend.modules.generation_queue.domain.errors import BudgetExhaustedError
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
)
from rag_backend.modules.generation_queue.domain.models import (
    CountsUpdate,
    GenerationRun,
)

if TYPE_CHECKING:
    from rag_backend.modules.generation_queue.application.job_handler import (
        HandlerDependencies,
    )


@dataclass(frozen=True)
class _Attempt:
    """The run snapshot and UUID claimed by one handler invocation."""

    run: GenerationRun
    attempt_id: UUID
    started_at: datetime


class _StaleAttemptError(Exception):
    """The attempt lost its fence while its executor was running."""


@dataclass(frozen=True, kw_only=True)
class _PhaseEvent:
    event_type: str
    phase: str
    outcome: str
    attempt: int | None = None
    error_code: str | None = None


_PHASE_MESSAGES = {
    EVENT_PHASE_STARTED: MESSAGE_PHASE_STARTED,
    EVENT_PHASE_SUCCEEDED: MESSAGE_PHASE_SUCCEEDED,
    EVENT_PHASE_FAILED: MESSAGE_PHASE_FAILED,
}
StartCallback = Callable[[], Awaitable[None]]
StepCallback = Callable[[], Awaitable[int]]


class _Tracker:
    """Counts phase starts and records their bounded timing events."""

    def __init__(
        self,
        deps: HandlerDependencies,
        attempt: _Attempt,
        on_start: StartCallback | None = None,
    ) -> None:
        self._deps = deps
        self._run_id = attempt.run.id
        self._attempt_id = attempt.attempt_id
        self._starts: dict[str, datetime] = {}
        self._on_start = on_start
        self._run_started = False
        self.counts = attempt.run.counts

    async def ensure_started(self) -> None:
        if self._run_started:
            return
        self._run_started = True
        if self._on_start is not None:
            await self._on_start()

    async def begin(self, phase: str) -> None:
        started = self._deps.clock.now()
        await self._save_start(phase, started)
        await self._emit_start(phase, started)
        self._raise_if_exhausted(phase)

    async def track_step(self, phase: str, step: StepCallback) -> int:
        started = self._deps.clock.now()
        await self._save_start(phase, started)
        if budget.exhausted(self.counts, phase, self._deps.budget) is not None:
            await self._emit_start(phase, started)
            self._raise_if_exhausted(phase)
        try:
            stepped = await step()
        except Exception:
            await self._emit_start(phase, started)
            raise
        if stepped == 0:
            await self._finish(phase, emit_event=False)
            return 0
        await self._emit_start(phase, started)
        await self.finish(phase)
        return stepped

    async def finish(self, phase: str) -> None:
        await self._finish(phase, emit_event=True)

    async def fail(self, error_code: str) -> None:
        for phase in tuple(self._starts):
            await self._close_phase(phase, error_code)

    async def _save_start(self, phase: str, started: datetime) -> None:
        self.counts = budget.begin(self.counts, phase)
        await self._save(phase)
        self._starts[phase] = started

    async def _emit_start(self, phase: str, started: datetime) -> None:
        await self.ensure_started()
        await self._phase_event(
            _PhaseEvent(
                event_type=EVENT_PHASE_STARTED,
                phase=phase,
                outcome=OUTCOME_RUNNING,
            ),
            occurred_at=started,
        )

    def _raise_if_exhausted(self, phase: str) -> None:
        error_code = budget.exhausted(self.counts, phase, self._deps.budget)
        if error_code is not None:
            raise BudgetExhaustedError(error_code)

    async def _finish(self, phase: str, *, emit_event: bool) -> None:
        attempt = self.counts.phase_attempts.get(phase)
        self.counts = budget.finish(self.counts, phase)
        await self._save(phase)
        if emit_event:
            await self._phase_event(
                _PhaseEvent(
                    event_type=EVENT_PHASE_SUCCEEDED,
                    phase=phase,
                    outcome=OUTCOME_SUCCEEDED,
                    attempt=attempt,
                )
            )
        self._starts.pop(phase, None)

    async def _save(self, phase: str) -> None:
        update = CountsUpdate(counts=self.counts, phase=phase)
        saved = await self._deps.store.save_counts(
            self._run_id, self._attempt_id, update
        )
        if not saved:
            raise _StaleAttemptError

    async def _close_phase(self, phase: str, error_code: str) -> None:
        await self._phase_event(
            _PhaseEvent(
                event_type=EVENT_PHASE_FAILED,
                phase=phase,
                outcome=OUTCOME_FAILED,
                error_code=error_code,
            )
        )
        self._starts.pop(phase, None)

    async def _phase_event(
        self, event: _PhaseEvent, *, occurred_at: datetime | None = None
    ) -> None:
        now = occurred_at or self._deps.clock.now()
        started = self._starts.get(event.phase, now)
        attempt = (
            event.attempt
            if event.attempt is not None
            else self.counts.phase_attempts.get(event.phase)
        )
        await record_generation_event(
            GenerationEventInput(
                event_type=event.event_type,
                outcome=event.outcome,
                phase=event.phase,
                occurred_at=now,
                duration_ms=_elapsed_ms(started, now),
                attempt=attempt,
                error_code=event.error_code,
                message_code=_PHASE_MESSAGES[event.event_type],
            )
        )


def _elapsed_ms(started: datetime, finished: datetime) -> int:
    return max(0, round((finished - started).total_seconds() * 1000))


__all__ = ["_Attempt", "_StaleAttemptError", "_Tracker"]
