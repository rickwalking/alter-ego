"""Ports of the generation queue; infrastructure implements them.

The store owns ``generation_runs``; the job queue wraps PgQueuer; the drive lock
is the only ownership primitive (one driver per project); executors run one kind
of work. Every port is async and owns its own session or connection.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from rag_backend.modules.generation_queue.domain.models import (
    AttemptDeadLetterCommand,
    CountsUpdate,
    DeadLetterCommand,
    GenerationRun,
    HeldJob,
    RetryCommand,
    StageCommand,
)


class GenerationRunStore(Protocol):
    """``generation_runs`` reads and compare-and-set writes."""

    async def get(self, run_id: UUID) -> GenerationRun | None:
        """The run, or None when it does not exist."""
        ...

    async def stage(self, command: StageCommand) -> bool:
        """Insert a queued run unless its dedupe key is active. True when inserted."""
        ...

    async def undispatched(self, limit: int) -> list[GenerationRun]:
        """Queued runs not handed to PgQueuer yet, oldest first."""
        ...

    async def set_job(self, run_id: UUID, job_id: int) -> None:
        """Record the PgQueuer job carrying the run."""
        ...

    async def clear_job(self, run_id: UUID) -> None:
        """Forget a job that no longer exists, so the dispatcher hands it over again."""
        ...

    async def dispatched_active(self, limit: int) -> list[GenerationRun]:
        """Active runs that carry a job id, oldest first."""
        ...

    async def mark_running(self, run_id: UUID) -> UUID | None:
        """Active → running with a fresh attempt UUID, or None when not active."""
        ...

    async def save_counts(
        self, run_id: UUID, attempt_id: UUID, update: CountsUpdate
    ) -> bool:
        """Persist counters only for the expected running attempt."""
        ...

    async def mark_succeeded(self, run_id: UUID, attempt_id: UUID) -> bool:
        """Running → succeeded only for the expected attempt."""
        ...

    async def mark_waiting(self, command: RetryCommand) -> bool:
        """Running → retry_wait only for the command's expected attempt."""
        ...

    async def mark_attempt_dead_letter(self, command: AttemptDeadLetterCommand) -> bool:
        """Running → dead_letter only for the command's expected attempt."""
        ...

    async def mark_dead_letter(self, command: DeadLetterCommand) -> bool:
        """Mirror a dispatcher-held job; False when it was not active."""
        ...

    async def requeue_dead_letter(self, run_id: UUID) -> bool:
        """Dead letter → queued with the failing phase's counter reset (CAS)."""
        ...

    async def other_active_for_project(self, project_id: str, run_id: UUID) -> bool:
        """True when another active run targets the project (it owns the phase)."""
        ...


class ActiveAutopilotSource(Protocol):
    """Autopilot runs that need driving (the dispatcher's safety net)."""

    async def active_run_ids(self, limit: int) -> list[tuple[str, str | None]]:
        """(run id, project id) of runs in queued, generating or reworking."""
        ...


class JobQueue(Protocol):
    """The PgQueuer side: transport only, never the source of truth."""

    async def find_job(self, dedupe_key: str) -> int | None:
        """The queued or picked job carrying ``dedupe_key``."""
        ...

    async def enqueue(self, run: GenerationRun) -> int | None:
        """Enqueue the run; None when PgQueuer already holds an active job for it."""
        ...

    async def kick(self, run: GenerationRun) -> int | None:
        """Reconcile priority, eligibility and any fenced picked replacement."""
        ...

    async def existing(self, job_ids: Sequence[int]) -> set[int]:
        """Which of these job ids still exist in the queue table."""
        ...

    async def held(self, limit: int) -> list[HeldJob]:
        """Jobs PgQueuer holds as ``failed``."""
        ...

    async def forget(self, job_id: int) -> None:
        """Delete a held job once it is mirrored as a dead letter."""
        ...


class DeadLetterNotices(Protocol):
    """Stages the one Telegram notice for a dead-lettered run."""

    async def stage(self, run: GenerationRun, error_code: str) -> None:
        """Write the notice to the outbox (the web delivers it)."""
        ...


class DriveLock(Protocol):
    """One driver per project, across processes."""

    def hold(self, keys: Sequence[str]) -> AbstractAsyncContextManager[None]:
        """Hold every key for the context; raise ``DriveLockBusyError`` when taken."""
        ...


class StepOutcome(StrEnum):
    """How a job ended when it did not raise.

    ``WAIT``: nothing to do now (a gate in flight, start spacing), come back later.
    ``YIELD``: stopped between phases (worker shutdown, step cap), come back at once.
    """

    DONE = "done"
    WAIT = "wait"
    YIELD = "yield"


class StepTracker(Protocol):
    """Counts each phase start against the budgets, before the work runs."""

    async def begin(self, phase: str) -> None:
        """Count a start; raise ``BudgetExhaustedError`` when over budget."""
        ...

    async def finish(self, phase: str) -> None:
        """The phase finished cleanly: take its start back."""
        ...

    async def track_step(self, phase: str, step: Callable[[], Awaitable[int]]) -> int:
        """Track a step only when it does work; zero leaves no phase events."""
        ...


class KindExecutor(Protocol):
    """Runs one kind of generation work."""

    async def lock_keys(self, run: GenerationRun) -> list[str]:
        """The drive-lock keys this run needs."""
        ...

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        """Do the work. Raise to fail; return WAIT to come back later."""
        ...


class Clock(Protocol):
    """Wall clock (injected for tests)."""

    def now(self) -> datetime:
        """The current aware UTC time."""
        ...
