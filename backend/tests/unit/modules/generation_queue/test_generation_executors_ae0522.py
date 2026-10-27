"""The autopilot drive and the dashboard resume, and the dispatcher."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from rag_backend.modules.generation_queue.application.dispatcher import (
    Dispatcher,
    DispatcherDependencies,
    DispatchReport,
)
from rag_backend.modules.generation_queue.application.executors import (
    AutopilotDriveDependencies,
    AutopilotDriveExecutor,
    RecoveryDependencies,
    WorkflowResumeDependencies,
    WorkflowResumeExecutor,
)
from rag_backend.modules.generation_queue.constants import (
    ERROR_HELD_JOB,
    MAX_STEPS_PER_JOB,
)
from rag_backend.modules.generation_queue.domain.errors import (
    PermanentGenerationError,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationStatus,
    HeldJob,
    WorkflowResumePayload,
    adopt_stage,
)
from rag_backend.modules.generation_queue.domain.ports import StepOutcome
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeActiveAutopilot,
    FakeNotices,
    FakeQueue,
    FakeRecovery,
    FakeStepper,
    FakeStore,
    make_run,
    resume_run,
)


@dataclass
class _Tracker:
    """Records begin/finish calls."""

    calls: list[str] = field(default_factory=list)

    async def begin(self, phase: str) -> None:
        self.calls.append(f"begin:{phase}")

    async def finish(self, phase: str) -> None:
        self.calls.append(f"finish:{phase}")

    async def track_step(self, phase: str, step: Callable[[], Awaitable[int]]) -> int:
        stepped = await step()
        if stepped == 0:
            return 0
        self.calls.extend((f"begin:{phase}", f"finish:{phase}"))
        return stepped


@dataclass
class _Resumer:
    payloads: list[WorkflowResumePayload] = field(default_factory=list)

    async def resume(self, payload: WorkflowResumePayload) -> None:
        self.payloads.append(payload)


def _drive(
    stepper: FakeStepper,
    *,
    store: FakeStore | None = None,
    recovery: FakeRecovery | None = None,
    stopping: bool = False,
) -> AutopilotDriveExecutor:
    return AutopilotDriveExecutor(
        AutopilotDriveDependencies(
            stepper=stepper,
            recovery=RecoveryDependencies(
                store=store or FakeStore(), recovery=recovery or FakeRecovery()
            ),
            stopping=lambda: stopping,
        )
    )


async def test_drive_steps_until_the_owner_has_to_act() -> None:
    """Scenario: One autopilot drive steps a run until the owner has to act"""
    stepper = FakeStepper(
        states=["queued", "generating", "generating", "awaiting_owner"]
    )
    tracker = _Tracker()
    outcome = await _drive(stepper).execute(make_run(), tracker)
    assert outcome is StepOutcome.DONE
    assert stepper.steps == 3
    assert tracker.calls[-2:] == ["begin:generating", "finish:generating"]


async def test_drive_waits_when_a_step_does_nothing() -> None:
    """Scenario: A drive with nothing to do comes back later"""
    stepper = FakeStepper(states=["generating"], stepped_values=[0])
    tracker = _Tracker()
    assert await _drive(stepper).execute(make_run(), tracker) is StepOutcome.WAIT
    assert tracker.calls == []


async def test_drive_of_a_finished_run_is_done() -> None:
    """Scenario: One autopilot drive steps a run until the owner has to act"""
    stepper = FakeStepper(states=["published"])
    assert await _drive(stepper).execute(make_run(), _Tracker()) is StepOutcome.DONE
    assert stepper.steps == 0


async def test_drive_yields_on_shutdown_and_at_the_step_cap() -> None:
    """Scenario: The worker stops at the next phase boundary on shutdown"""
    stopping = _drive(FakeStepper(states=["generating"]), stopping=True)
    assert await stopping.execute(make_run(), _Tracker()) is StepOutcome.YIELD
    endless = FakeStepper(states=["generating"] * (MAX_STEPS_PER_JOB + 5))
    assert await _drive(endless).execute(make_run(), _Tracker()) is StepOutcome.YIELD
    assert endless.steps == MAX_STEPS_PER_JOB


async def test_drive_reaps_an_orphaned_phase_and_redrives_it() -> None:
    """Scenario: A run interrupted by a deploy resumes by itself"""
    recovery = FakeRecovery(in_progress_now=True, parked=True, phase="content")
    stepper = FakeStepper(states=["generating", "awaiting_owner"])
    tracker = _Tracker()
    outcome = await _drive(stepper, recovery=recovery).execute(make_run(), tracker)
    assert outcome is StepOutcome.DONE
    assert recovery.reaped == ["p1"]
    assert recovery.redriven == ["p1"]
    assert tracker.calls[:2] == ["begin:recovery:content", "finish:recovery:content"]


async def test_drive_waits_while_a_dashboard_resume_owns_the_project() -> None:
    """Scenario: A queued dashboard resume owns its in-progress project"""
    store = FakeStore()
    store.add(resume_run())
    recovery = FakeRecovery(in_progress_now=True, parked=True)
    stepper = FakeStepper(states=["generating"])
    drive = _drive(stepper, store=store, recovery=recovery)
    assert await drive.execute(make_run(), _Tracker()) is StepOutcome.WAIT
    assert recovery.reaped == []
    assert stepper.steps == 0


async def test_drive_lock_keys_cover_the_run_and_its_project() -> None:
    """Scenario: Two drivers claim the same project and exactly one drives"""
    keys = await _drive(FakeStepper(states=["generating"])).lock_keys(make_run())
    assert keys == ["autopilot:r1", "project:p1"]
    no_project = FakeStepper(states=["queued"], project_id=None)
    assert await _drive(no_project).lock_keys(make_run()) == ["autopilot:r1"]


async def test_drive_with_a_broken_payload_is_permanent() -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    with pytest.raises(PermanentGenerationError):
        await _drive(FakeStepper(states=["queued"])).execute(
            make_run(payload={}), _Tracker()
        )


def _resume(recovery: FakeRecovery, resumer: _Resumer) -> WorkflowResumeExecutor:
    return WorkflowResumeExecutor(
        WorkflowResumeDependencies(
            resumer=resumer,
            recovery=RecoveryDependencies(store=FakeStore(), recovery=recovery),
        )
    )


async def test_resume_runs_the_review_decision_once() -> None:
    """Scenario: The dashboard resume is queued, not run in the web process"""
    resumer = _Resumer()
    tracker = _Tracker()
    executor = _resume(FakeRecovery(in_progress_now=True), resumer)
    run = resume_run()
    assert await executor.lock_keys(run) == ["project:p1"]
    assert await executor.execute(run, tracker) is StepOutcome.DONE
    assert [payload.action for payload in resumer.payloads] == ["approve"]
    assert tracker.calls == ["begin:outline", "finish:outline"]


async def test_repicked_resume_recovers_without_resending_the_decision() -> None:
    """Scenario: A re-picked dashboard resume does not re-apply the review decision"""
    resumer = _Resumer()
    recovery = FakeRecovery(in_progress_now=True, parked=True)
    run = resume_run(last_phase="outline", attempts=1)
    assert await _resume(recovery, resumer).execute(run, _Tracker()) is StepOutcome.DONE
    assert resumer.payloads == []
    assert recovery.reaped == ["p1"]
    assert recovery.redriven == ["p1"]


async def test_adopted_project_is_recovered_on_its_first_pick() -> None:
    """Scenario: A dashboard resume a deploy killed before the cutover resumes in the worker"""
    resumer = _Resumer()
    recovery = FakeRecovery(in_progress_now=True, parked=True)
    stage = adopt_stage("p1", "T")
    run = resume_run(dedupe_key=stage.dedupe_key, payload=stage.payload)
    assert await _resume(recovery, resumer).execute(run, _Tracker()) is StepOutcome.DONE
    assert resumer.payloads == []
    assert recovery.reaped == ["p1"]
    assert recovery.redriven == ["p1"]


def _dispatcher(
    store: FakeStore,
    queue: FakeQueue,
    active: FakeActiveAutopilot,
    notices: FakeNotices,
) -> Dispatcher:
    return Dispatcher(
        DispatcherDependencies(
            store=store, queue=queue, autopilot=active, notices=notices
        )
    )


async def test_dispatcher_stages_and_hands_over_once() -> None:
    """Scenario: The dispatcher stages and hands over the queued work"""
    store, queue, notices = FakeStore(), FakeQueue(), FakeNotices()
    queued = store.add(resume_run())
    active = FakeActiveAutopilot(runs=[("r7", "p7")])
    report = await _dispatcher(store, queue, active, notices).run_once()
    assert report == DispatchReport(staged=1, dispatched=2)
    assert store.runs[queued.id].pgq_job_id is not None
    again = await _dispatcher(store, queue, active, notices).run_once()
    assert again == DispatchReport()
    assert len(queue.jobs) == 2


async def test_dispatcher_reuses_a_job_enqueued_before_a_crash() -> None:
    """Scenario: The same confirmation twice queues one run"""
    store, queue = FakeStore(), FakeQueue(jobs={"resume:p1:2": 55}, alive={55})
    run = store.add(resume_run())
    await _dispatcher(store, queue, FakeActiveAutopilot(), FakeNotices()).run_once()
    assert store.runs[run.id].pgq_job_id == 55
    assert queue.next_id == 100


async def test_dispatcher_hands_over_a_lost_job_again() -> None:
    """Scenario: A lost job is handed over again"""
    store, queue = FakeStore(), FakeQueue()
    run = store.add(resume_run(pgq_job_id=9, status=GenerationStatus.RETRY_WAIT))
    report = await _dispatcher(
        store, queue, FakeActiveAutopilot(), FakeNotices()
    ).run_once()
    assert report.lost == 1
    assert store.runs[run.id].status is GenerationStatus.QUEUED
    assert store.runs[run.id].pgq_job_id is None


async def test_dispatcher_mirrors_a_held_job_once() -> None:
    """Scenario: A held job the handler did not mirror becomes a dead letter"""
    store, notices = FakeStore(), FakeNotices()
    run = store.add(make_run(status=GenerationStatus.RUNNING, pgq_job_id=3))
    queue = FakeQueue(
        alive={3},
        held_jobs=[
            HeldJob(job_id=3, generation_run_id=run.id),
            HeldJob(job_id=4, generation_run_id=None),
            HeldJob(job_id=5, generation_run_id=uuid4()),
        ],
    )
    report = await _dispatcher(store, queue, FakeActiveAutopilot(), notices).run_once()
    assert report.dead_lettered == 1
    assert store.runs[run.id].status is GenerationStatus.DEAD_LETTER
    assert notices.staged == [(run.id, ERROR_HELD_JOB)]
    assert queue.forgotten == [3, 4, 5]
    queue.held_jobs = [HeldJob(job_id=3, generation_run_id=run.id)]
    await _dispatcher(store, queue, FakeActiveAutopilot(), notices).run_once()
    assert len(notices.staged) == 1


async def test_repicked_resume_leaves_a_project_a_newer_resume_owns() -> None:
    """Scenario: A queued dashboard resume owns its in-progress project"""
    store = FakeStore()
    store.add(resume_run(dedupe_key="resume:p1:3"))
    recovery = FakeRecovery(in_progress_now=True, parked=True)
    executor = WorkflowResumeExecutor(
        WorkflowResumeDependencies(
            resumer=_Resumer(),
            recovery=RecoveryDependencies(store=store, recovery=recovery),
        )
    )
    run = resume_run(last_phase="outline", attempts=1)
    assert await executor.execute(run, _Tracker()) is StepOutcome.DONE
    assert recovery.reaped == []
    assert recovery.redriven == []
