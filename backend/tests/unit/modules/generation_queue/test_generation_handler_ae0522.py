"""The job handler: lock, executor, budgets, and the verdict PgQueuer gets."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from rag_backend.modules.generation_queue.application.job_handler import (
    GenerationJobHandler,
    HandlerDependencies,
    Verdict,
    VerdictKind,
)
from rag_backend.modules.generation_queue.constants import (
    ERROR_PHASE_BUDGET,
    ERROR_UNKNOWN_KIND,
)
from rag_backend.modules.generation_queue.domain.errors import (
    PermanentGenerationError,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationStatus,
)
from rag_backend.modules.generation_queue.domain.ports import (
    KindExecutor,
    StepOutcome,
)
from tests.unit.modules.generation_queue.queue_fakes import (
    NOW,
    FakeLock,
    FakeNotices,
    FakeStore,
    FixedClock,
    ScriptedExecutor,
    make_run,
)


def _handler(
    store: FakeStore,
    executor: KindExecutor,
    *,
    lock: FakeLock | None = None,
    notices: FakeNotices | None = None,
) -> GenerationJobHandler:
    return GenerationJobHandler(
        HandlerDependencies(
            store=store,
            lock=lock or FakeLock(),
            executors={GenerationKind.AUTOPILOT_DRIVE: executor},
            notices=notices or FakeNotices(),
            clock=FixedClock(),
            is_provider_error=lambda _exc: False,
            uniform=lambda low, _high: low,
        )
    )


async def test_done_marks_the_run_succeeded() -> None:
    """Scenario: One autopilot drive steps a run until the owner has to act"""
    store = FakeStore()
    run = store.add(make_run())
    lock = FakeLock()
    verdict = await _handler(store, ScriptedExecutor(), lock=lock).handle(run.id)
    assert verdict == Verdict(VerdictKind.DONE)
    assert store.runs[run.id].status is GenerationStatus.SUCCEEDED
    assert lock.held == [[f"run:{run.id}"]]
    assert store.runs[run.id].attempts == 0


async def test_wait_retries_later_keeping_the_job() -> None:
    """Scenario: A drive with nothing to do comes back later"""
    store = FakeStore()
    run = store.add(make_run())
    verdict = await _handler(store, ScriptedExecutor(StepOutcome.WAIT)).handle(run.id)
    assert verdict == Verdict(VerdictKind.RETRY, timedelta(seconds=60))
    assert store.runs[run.id].status is GenerationStatus.RETRY_WAIT
    assert store.waits[0].next_attempt_at == NOW + timedelta(seconds=60)


async def test_yield_comes_back_at_once() -> None:
    """Scenario: The worker stops at the next phase boundary on shutdown"""
    store = FakeStore()
    run = store.add(make_run())
    verdict = await _handler(store, ScriptedExecutor(StepOutcome.YIELD)).handle(run.id)
    assert verdict == Verdict(VerdictKind.RETRY, timedelta(0))


async def test_transient_failure_retries_with_backoff() -> None:
    """Scenario: A transient failure retries with backoff and jitter"""
    store = FakeStore()
    run = store.add(make_run())
    executor = ScriptedExecutor(error=TimeoutError("provider"))
    verdict = await _handler(store, executor).handle(run.id)
    assert verdict == Verdict(VerdictKind.RETRY, timedelta(seconds=24))
    stored = store.runs[run.id]
    assert stored.status is GenerationStatus.RETRY_WAIT
    assert stored.last_error_code == "transient"
    assert store.waits[0].error == "TimeoutError: provider"
    assert stored.phase_attempts == {"research": 1}


async def test_permanent_failure_dead_letters_with_one_notice() -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    store = FakeStore()
    notices = FakeNotices()
    run = store.add(make_run())
    executor = ScriptedExecutor(error=ValueError("unparseable outline"))
    verdict = await _handler(store, executor, notices=notices).handle(run.id)
    assert verdict == Verdict(VerdictKind.HOLD)
    assert store.runs[run.id].status is GenerationStatus.DEAD_LETTER
    assert store.dead[0].error_code == "permanent"
    assert store.dead[0].error == "ValueError: unparseable outline"
    assert notices.staged == [(run.id, "permanent")]


async def test_exhausted_phase_budget_dead_letters_before_work() -> None:
    """Scenario: A phase that keeps failing is parked once its budget is spent"""
    store = FakeStore()
    notices = FakeNotices()
    run = store.add(make_run(attempts=3, phase_attempts={"research": 3}))
    executor = ScriptedExecutor(error=AssertionError("must not run"))
    verdict = await _handler(store, executor, notices=notices).handle(run.id)
    assert verdict == Verdict(VerdictKind.HOLD)
    assert store.runs[run.id].last_error_code == ERROR_PHASE_BUDGET
    assert store.saved[-1].counts.phase_attempts == {"research": 4}
    assert notices.staged == [(run.id, ERROR_PHASE_BUDGET)]


async def test_busy_lock_comes_back_in_two_minutes() -> None:
    """Scenario: Two drivers claim the same project and exactly one drives"""
    store = FakeStore()
    run = store.add(make_run())
    executor = ScriptedExecutor()
    verdict = await _handler(store, executor, lock=FakeLock(busy=True)).handle(run.id)
    assert verdict == Verdict(VerdictKind.RETRY, timedelta(seconds=120))
    assert store.runs[run.id].last_error_code == "drive_lock_busy"
    assert store.runs[run.id].attempts == 0


async def test_unknown_or_finished_runs() -> None:
    """Scenario: The same confirmation twice queues one run"""
    store = FakeStore()
    handler = _handler(store, ScriptedExecutor())
    assert await handler.handle(uuid4()) == Verdict(VerdictKind.DONE)
    done = store.add(make_run(status=GenerationStatus.SUCCEEDED))
    assert await handler.handle(done.id) == Verdict(VerdictKind.DONE)
    assert store.runs[done.id].status is GenerationStatus.SUCCEEDED


async def test_unknown_kind_dead_letters() -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    store = FakeStore()
    run = store.add(make_run(kind=GenerationKind.WORKFLOW_RESUME))
    verdict = await _handler(store, ScriptedExecutor()).handle(run.id)
    assert verdict == Verdict(VerdictKind.HOLD)
    assert store.runs[run.id].last_error_code == ERROR_UNKNOWN_KIND


async def test_a_second_dead_letter_stages_no_second_notice() -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    store = FakeStore()
    notices = FakeNotices()
    run = store.add(make_run())
    handler = _handler(
        store, ScriptedExecutor(error=PermanentGenerationError("x")), notices=notices
    )
    await handler.handle(run.id)
    assert await handler.handle(run.id) == Verdict(VerdictKind.DONE)
    assert len(notices.staged) == 1
