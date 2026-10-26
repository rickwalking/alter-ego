"""In-memory fakes of the generation queue ports."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from rag_backend.modules.generation_queue.constants import ACTIVE_STATUSES
from rag_backend.modules.generation_queue.domain import budget
from rag_backend.modules.generation_queue.domain.drive_ports import AutopilotView
from rag_backend.modules.generation_queue.domain.errors import DriveLockBusyError
from rag_backend.modules.generation_queue.domain.models import (
    ATTEMPT_ID_KEY,
    AttemptDeadLetterCommand,
    CountsUpdate,
    DeadLetterCommand,
    GenerationKind,
    GenerationRun,
    GenerationStatus,
    HeldJob,
    RetryCommand,
    StageCommand,
    WorkflowResumePayload,
)
from rag_backend.modules.generation_queue.domain.ports import StepOutcome, StepTracker

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


class FixedClock:
    """Always ``NOW``."""

    @staticmethod
    def now() -> datetime:
        """The fixed time."""
        return NOW


def make_run(**overrides: object) -> GenerationRun:
    """A queued autopilot drive run, with any field overridden."""
    run = GenerationRun(
        id=uuid4(),
        kind=GenerationKind.AUTOPILOT_DRIVE,
        dedupe_key="autopilot:r1",
        status=GenerationStatus.QUEUED,
        payload={"autopilot_run_id": "r1"},
        autopilot_run_id="r1",
        created_at=NOW,
    )
    return replace(run, **overrides)


def resume_run(**overrides: object) -> GenerationRun:
    """A queued dashboard resume run."""
    payload = WorkflowResumePayload(
        project_id="p1", action="approve", reviewer_id="u1", project_title="T"
    )
    fields: dict[str, object] = {
        "kind": GenerationKind.WORKFLOW_RESUME,
        "dedupe_key": "resume:p1:2",
        "payload": payload.dump(),
        "autopilot_run_id": None,
        "carousel_project_id": "p1",
    }
    fields.update(overrides)
    return make_run(**fields)


def _owns_attempt(run: GenerationRun, attempt_id: UUID) -> bool:
    return run.status is GenerationStatus.RUNNING and run.attempt_id == attempt_id


@dataclass
class FakeStore:
    """``GenerationRunStore`` in memory."""

    runs: dict[UUID, GenerationRun] = field(default_factory=dict)
    waits: list[RetryCommand] = field(default_factory=list)
    dead: list[DeadLetterCommand | AttemptDeadLetterCommand] = field(
        default_factory=list
    )
    saved: list[CountsUpdate] = field(default_factory=list)

    def add(self, run: GenerationRun) -> GenerationRun:
        """Store ``run`` and return it."""
        self.runs[run.id] = run
        return run

    async def get(self, run_id: UUID) -> GenerationRun | None:
        """The stored run."""
        return self.runs.get(run_id)

    async def stage(self, command: StageCommand) -> bool:
        """Insert unless the key is active."""
        if any(
            run.dedupe_key == command.dedupe_key and run.status.value in ACTIVE_STATUSES
            for run in self.runs.values()
        ):
            return False
        self.add(
            make_run(
                kind=command.kind,
                dedupe_key=command.dedupe_key,
                payload=command.payload,
                autopilot_run_id=command.autopilot_run_id,
                carousel_project_id=command.carousel_project_id,
            )
        )
        return True

    async def undispatched(self, limit: int) -> list[GenerationRun]:
        """Queued runs without a job."""
        return [
            run
            for run in self.runs.values()
            if run.status is GenerationStatus.QUEUED and run.pgq_job_id is None
        ][:limit]

    async def set_job(self, run_id: UUID, job_id: int) -> None:
        """Record the job."""
        self.runs[run_id] = replace(self.runs[run_id], pgq_job_id=job_id)

    async def clear_job(self, run_id: UUID) -> None:
        """Forget the job."""
        self.runs[run_id] = replace(
            self.runs[run_id], pgq_job_id=None, status=GenerationStatus.QUEUED
        )

    async def dispatched_active(self, limit: int) -> list[GenerationRun]:
        """Active runs with a job."""
        return [
            run
            for run in self.runs.values()
            if run.status.value in ACTIVE_STATUSES and run.pgq_job_id is not None
        ][:limit]

    async def mark_running(self, run_id: UUID) -> UUID | None:
        """Active → running with a fresh attempt UUID."""
        run = self.runs[run_id]
        if run.status.value not in ACTIVE_STATUSES:
            return None
        attempt_id = uuid4()
        payload = {**run.payload, ATTEMPT_ID_KEY: str(attempt_id)}
        self.runs[run_id] = replace(
            run, status=GenerationStatus.RUNNING, payload=payload
        )
        return attempt_id

    async def save_counts(
        self, run_id: UUID, attempt_id: UUID, update: CountsUpdate
    ) -> bool:
        """Persist counters only for the current running attempt."""
        if not _owns_attempt(self.runs[run_id], attempt_id):
            return False
        self.saved.append(update)
        self.runs[run_id] = replace(
            self.runs[run_id],
            attempts=update.counts.attempts,
            phase_attempts=dict(update.counts.phase_attempts),
            last_phase=update.phase,
        )
        return True

    async def mark_succeeded(self, run_id: UUID, attempt_id: UUID) -> bool:
        """Running → succeeded only for the current attempt."""
        if not _owns_attempt(self.runs[run_id], attempt_id):
            return False
        self.runs[run_id] = replace(
            self.runs[run_id], status=GenerationStatus.SUCCEEDED
        )
        return True

    async def mark_waiting(self, command: RetryCommand) -> bool:
        """Running → retry_wait only for the current attempt."""
        if not _owns_attempt(self.runs[command.run_id], command.attempt_id):
            return False
        self.waits.append(command)
        self.runs[command.run_id] = replace(
            self.runs[command.run_id],
            status=GenerationStatus.RETRY_WAIT,
            last_error_code=command.error_code,
        )
        return True

    async def mark_attempt_dead_letter(self, command: AttemptDeadLetterCommand) -> bool:
        """Running → dead_letter only for the current attempt."""
        if not _owns_attempt(self.runs[command.run_id], command.attempt_id):
            return False
        self.dead.append(command)
        self.runs[command.run_id] = replace(
            self.runs[command.run_id],
            status=GenerationStatus.DEAD_LETTER,
            last_error_code=command.error_code,
        )
        return True

    async def mark_dead_letter(self, command: DeadLetterCommand) -> bool:
        """Active → dead_letter for the dispatcher's held-job path."""
        run = self.runs[command.run_id]
        if run.status.value not in ACTIVE_STATUSES:
            return False
        self.dead.append(command)
        self.runs[command.run_id] = replace(
            run, status=GenerationStatus.DEAD_LETTER, last_error_code=command.error_code
        )
        return True

    async def requeue_dead_letter(self, run_id: UUID) -> bool:
        """Dead letter → queued with the failing phase reset."""
        run = self.runs[run_id]
        if run.status is not GenerationStatus.DEAD_LETTER:
            return False
        counts = budget.reset_phase(run.counts, run.last_phase)
        self.runs[run_id] = replace(
            run,
            status=GenerationStatus.QUEUED,
            attempts=counts.attempts,
            phase_attempts=dict(counts.phase_attempts),
        )
        return True

    async def other_active_for_project(self, project_id: str, run_id: UUID) -> bool:
        """Another active resume targets the project."""
        return any(
            run.id != run_id
            and run.carousel_project_id == project_id
            and run.kind is GenerationKind.WORKFLOW_RESUME
            and run.status.value in ACTIVE_STATUSES
            for run in self.runs.values()
        )


@dataclass
class FakeNotices:
    """Records the staged owner notices."""

    staged: list[tuple[UUID, str]] = field(default_factory=list)

    async def stage(self, run: GenerationRun, error_code: str) -> None:
        """Record the notice."""
        self.staged.append((run.id, error_code))


@dataclass
class FakeLock:
    """A drive lock that is free unless ``busy``."""

    busy: bool = False
    held: list[list[str]] = field(default_factory=list)

    @asynccontextmanager
    async def hold(self, keys: Sequence[str]) -> AsyncIterator[None]:
        """Hold the keys, or raise when busy."""
        if self.busy:
            raise DriveLockBusyError
        self.held.append(list(keys))
        yield


@dataclass
class ScriptedExecutor:
    """Returns ``outcome`` or raises ``error``; steps the given phases first."""

    outcome: StepOutcome = StepOutcome.DONE
    error: Exception | None = None
    phases: tuple[str, ...] = ("research",)
    finish: bool = True

    async def lock_keys(self, run: GenerationRun) -> list[str]:
        """One key per run."""
        return [f"run:{run.id}"]

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        """Begin (and finish) each phase, then end as scripted."""
        for phase in self.phases:
            await tracker.begin(phase)
            if self.error is not None:
                raise self.error
            if self.finish:
                await tracker.finish(phase)
        return self.outcome


@dataclass
class FakeStepper:
    """An autopilot run that walks ``states``; each step moves one state on."""

    states: list[str]
    project_id: str | None = "p1"
    steps: int = 0
    stepped_values: list[int] = field(default_factory=list)

    async def view(self, run_id: str) -> AutopilotView | None:
        """The current state."""
        state = self.states[min(self.steps, len(self.states) - 1)]
        return AutopilotView(state=state, project_id=self.project_id, phase=state)

    async def step(self, run_id: str) -> int:
        """Advance one state (or report nothing to do)."""
        value = self.stepped_values[self.steps] if self.stepped_values else 1
        if value:
            self.steps += 1
        return value


@dataclass
class FakeRecovery:
    """Project recovery that records what it did."""

    in_progress_now: bool = False
    parked: bool = False
    phase: str = "outline"
    reaped: list[str] = field(default_factory=list)
    redriven: list[str] = field(default_factory=list)

    async def current_phase(self, project_id: str) -> str:
        """The phase."""
        return self.phase

    async def in_progress(self, project_id: str) -> bool:
        """Whether the row says in progress."""
        return self.in_progress_now

    async def reap(self, project_id: str) -> bool:
        """Reap."""
        self.reaped.append(project_id)
        self.in_progress_now = False
        return True

    async def redrive_if_parked(self, project_id: str) -> bool:
        """Re-drive when parked."""
        if not self.parked:
            return False
        self.redriven.append(project_id)
        self.parked = False
        return True


@dataclass
class FakeQueue:
    """``JobQueue`` in memory."""

    jobs: dict[str, int] = field(default_factory=dict)
    alive: set[int] = field(default_factory=set)
    held_jobs: list[HeldJob] = field(default_factory=list)
    forgotten: list[int] = field(default_factory=list)
    next_id: int = 100
    kicked: list[UUID] = field(default_factory=list)
    enqueued: list[UUID] = field(default_factory=list)

    async def find_job(self, dedupe_key: str) -> int | None:
        """The job with the key."""
        return self.jobs.get(dedupe_key)

    async def enqueue(self, run: GenerationRun) -> int | None:
        """A new job id, or the active dedupe match."""
        existing = self.jobs.get(run.dedupe_key)
        if existing is not None:
            return existing
        self.next_id += 1
        self.jobs[run.dedupe_key] = self.next_id
        self.alive.add(self.next_id)
        self.enqueued.append(run.id)
        return self.next_id

    async def kick(self, run: GenerationRun) -> int | None:
        """Return the active job or enqueue a missing one."""
        self.kicked.append(run.id)
        existing = self.jobs.get(run.dedupe_key)
        if existing is not None:
            return existing
        return await self.enqueue(run)

    async def existing(self, job_ids: Sequence[int]) -> set[int]:
        """The live ones."""
        return {job for job in job_ids if job in self.alive}

    async def held(self, limit: int) -> list[HeldJob]:
        """The held jobs."""
        return list(self.held_jobs[:limit])

    async def forget(self, job_id: int) -> None:
        """Drop a held job."""
        self.forgotten.append(job_id)
        self.held_jobs = [job for job in self.held_jobs if job.job_id != job_id]


@dataclass
class FakeActiveAutopilot:
    """Active autopilot runs."""

    runs: list[tuple[str, str | None]] = field(default_factory=list)

    async def active_run_ids(self, limit: int) -> list[tuple[str, str | None]]:
        """The configured runs."""
        return self.runs[:limit]
