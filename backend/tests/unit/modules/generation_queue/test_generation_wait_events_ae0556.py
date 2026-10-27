"""Bounded waiting events for autopilot and lock contention.

Feature: carousel_generation_log_ae0556.feature
"""

from rag_backend.modules.generation_queue.application.executors import (
    AutopilotDriveDependencies,
    AutopilotDriveExecutor,
    RecoveryDependencies,
)
from rag_backend.modules.generation_queue.application.job_handler import (
    GenerationJobHandler,
    HandlerDependencies,
    VerdictKind,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeLock,
    FakeNotices,
    FakeRecovery,
    FakeStepper,
    FakeStore,
    FixedClock,
    ScriptedExecutor,
    make_run,
    resume_run,
)
from tests.unit.modules.generation_queue.test_generation_events_ae0556 import (
    FakeEventRecorder,
    _handler,
)


def _autopilot_executor(stepper: FakeStepper) -> AutopilotDriveExecutor:
    return AutopilotDriveExecutor(
        AutopilotDriveDependencies(
            stepper=stepper,
            recovery=RecoveryDependencies(store=FakeStore(), recovery=FakeRecovery()),
            stopping=lambda: False,
        )
    )


async def test_repeated_autopilot_waits_record_only_the_streak_boundaries() -> None:
    """Scenario: Waiting autopilot work does not flood the generation log"""
    store = FakeStore()
    run = store.add(make_run())
    recorder = FakeEventRecorder()
    stepper = FakeStepper(states=["generating", "awaiting_owner"], stepped_values=[0])
    handler = _handler(
        store,
        _autopilot_executor(stepper),
        recorder,
        kind=GenerationKind.AUTOPILOT_DRIVE,
    )

    for _ in range(6):
        verdict = await handler.handle(run.id)
        assert verdict.kind is VerdictKind.RETRY

    assert [event.event_type for _, event in recorder.records] == ["run_waiting"]
    assert len(store.waits) == 6

    stepper.stepped_values = [1]
    verdict = await handler.handle(run.id)

    assert verdict.kind is VerdictKind.DONE
    assert [event.event_type for _, event in recorder.records] == [
        "run_waiting",
        "run_started",
        "phase_started",
        "phase_succeeded",
        "run_succeeded",
    ]
    resumed = recorder.records[1][1]
    assert resumed.details["resumed"] is True


async def test_repeated_busy_locks_record_one_waiting_event() -> None:
    """Scenario: Waiting autopilot work does not flood the generation log"""
    store = FakeStore()
    run = store.add(resume_run())
    recorder = FakeEventRecorder()
    lock = FakeLock(busy=True)
    handler = GenerationJobHandler(
        HandlerDependencies(
            store=store,
            lock=lock,
            executors={GenerationKind.WORKFLOW_RESUME: ScriptedExecutor()},
            notices=FakeNotices(),
            clock=FixedClock(),
            is_provider_error=lambda _exc: False,
            events=recorder,
        )
    )

    for _ in range(5):
        verdict = await handler.handle(run.id)
        assert verdict.kind is VerdictKind.RETRY

    assert [event.event_type for _, event in recorder.records] == ["run_waiting"]
    lock.busy = False
    assert (await handler.handle(run.id)).kind is VerdictKind.DONE
    assert [event.event_type for _, event in recorder.records] == [
        "run_waiting",
        "run_started",
        "phase_started",
        "phase_succeeded",
        "run_succeeded",
    ]
