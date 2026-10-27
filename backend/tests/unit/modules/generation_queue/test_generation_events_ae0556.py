"""Safe generation events and queue timeline instrumentation.

Feature: carousel_generation_log_ae0556.feature
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import DBAPIError
from structlog.testing import capture_logs

from rag_backend.modules.generation_queue.application.dispatcher import (
    Dispatcher,
    DispatcherDependencies,
)
from rag_backend.modules.generation_queue.application.generation_events import (
    NO_RUN_COMPLETION,
    generation_event_scope,
    record_generation_event,
    set_generation_event_project,
)
from rag_backend.modules.generation_queue.application.job_handler import (
    GenerationJobHandler,
    HandlerDependencies,
    VerdictKind,
)
from rag_backend.modules.generation_queue.domain.failure_metadata import (
    safe_failure_metadata,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    EVENT_WRITE_TIMEOUT_SECONDS,
    GenerationEventInput,
    GenerationEventRun,
    GenerationRunCompletion,
    sanitize_event,
    sanitize_event_details,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationRun,
)
from rag_backend.modules.generation_queue.domain.ports import (
    KindExecutor,
    StepOutcome,
    StepTracker,
)
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeActiveAutopilot,
    FakeLock,
    FakeNotices,
    FakeQueue,
    FakeStore,
    FixedClock,
    ScriptedExecutor,
    resume_run,
)

PLANTED_SECRET = "planted-secret-prompt-value"
PLANTED_SQL = "SELECT * FROM generation_runs WHERE token = %(token)s"


@dataclass
class FakeEventRecorder:
    records: list[tuple[GenerationEventRun, GenerationEventInput]] = field(
        default_factory=list
    )
    error: Exception | None = None
    delay: float = 0
    calls: list[str] = field(default_factory=list)

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        self.records.append((run, event))
        self.calls.append(event.event_type)
        return True


def _run(project_id: str | None = "p1") -> GenerationEventRun:
    return GenerationEventRun(
        id=uuid4(), kind=GenerationKind.WORKFLOW_RESUME, carousel_project_id=project_id
    )


def _event(event_type: str = "run_failed") -> GenerationEventInput:
    return GenerationEventInput(
        event_type=event_type,
        outcome="failed",
        occurred_at=datetime(2026, 10, 26, 12, tzinfo=UTC),
    )


@dataclass
class _FencingExecutor:
    store: FakeStore

    async def lock_keys(self, run: GenerationRun) -> list[str]:
        del run
        return []

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        await tracker.begin("content")
        await self.store.mark_running(run.id)
        raise TimeoutError(PLANTED_SECRET)


@dataclass
class _LateProjectExecutor:
    project_id: str

    async def lock_keys(self, run: GenerationRun) -> list[str]:
        del run
        return []

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        del run
        set_generation_event_project(self.project_id)
        await tracker.begin("content")
        await tracker.finish("content")
        return StepOutcome.DONE


def _handler(
    store: FakeStore,
    executor: KindExecutor,
    recorder: FakeEventRecorder,
    completion: GenerationRunCompletion | None = None,
    kind: GenerationKind = GenerationKind.WORKFLOW_RESUME,
) -> GenerationJobHandler:
    return GenerationJobHandler(
        HandlerDependencies(
            store=store,
            lock=FakeLock(),
            executors={kind: executor},
            notices=FakeNotices(),
            clock=FixedClock(),
            is_provider_error=lambda _exc: False,
            uniform=lambda low, _high: low,
            events=recorder,
            completion=completion or NO_RUN_COMPLETION,
        )
    )


async def test_stored_events_exclude_sensitive_failure_content() -> None:
    """Scenario: Stored events exclude sensitive failure content"""
    error = DBAPIError(
        PLANTED_SQL, {"token": PLANTED_SECRET}, Exception(PLANTED_SECRET)
    )
    metadata = safe_failure_metadata(error, "database_error")
    details = sanitize_event_details({
        "prompt": PLANTED_SECRET,
        "sql": PLANTED_SQL,
        "params": {"token": PLANTED_SECRET},
        "model": "gpt-image-2",
        "score": float("nan"),
        "violation_count": 3,
    })

    assert metadata == {"error_type": "DBAPIError", "error_code": "database_error"}
    assert details == {
        "model": "gpt-image-2",
        "violation_count": 3,
        "truncated": True,
    }
    serialized = json.dumps({"metadata": metadata, "details": details})
    assert PLANTED_SECRET not in serialized
    assert PLANTED_SQL not in serialized
    assert len(json.dumps(details).encode()) <= 4096
    assert sanitize_event_details({"model": PLANTED_SECRET}) == {"truncated": True}
    assert sanitize_event_details({"model": "gpt-planted-secret"}) == {
        "truncated": True
    }
    oversized = {f"unknown_{index}": "x" for index in range(10000)}
    assert sanitize_event_details(oversized) == {"truncated": True}
    started = time.monotonic()
    huge = sanitize_event(
        GenerationEventInput(
            event_type="x" * 1000000,
            outcome="x" * 25,
            attempt=40000,
            details={"model": "x" * 1000000},
        )
    )
    assert time.monotonic() - started < EVENT_WRITE_TIMEOUT_SECONDS
    assert huge.outcome == "unknown"
    assert huge.attempt is None
    assert huge.details == {"truncated": True}
    many = {
        "action": "retry",
        "attempt": 1,
        "autopilot_run_id": str(uuid4()),
        "blocking_count": 1,
        "byte_count": 1,
        "delay_seconds": 1,
        "error_type": "TimeoutError",
        "failed_count": 1,
        "image_job_id": str(uuid4()),
        "job_status": "failed",
        "language": "pt",
        "lowest_score": 80.0,
        "model": "gpt-image-2",
        "page_count": 1,
        "policy_version": "v1",
        "provider": "openai",
        "reason": "transient",
        "result": "failed",
        "resumed": True,
        "reused": False,
        "score": 80.0,
        "scored_count": 1,
        "size": "1536x1024",
        "slide_index": 1,
        "status": "failed",
        "total_count": 1,
        "unscored_count": 0,
        "violation_count": 1,
    }
    bounded = sanitize_event_details(many)
    assert len(bounded) <= 24
    assert len(json.dumps(bounded).encode()) <= 4096


async def test_recorder_failures_do_not_change_a_successful_generation() -> None:
    """Scenario: Event storage failures never break generation"""
    store = FakeStore()
    run = store.add(resume_run())
    failure = DBAPIError(
        PLANTED_SQL, {"token": PLANTED_SECRET}, Exception(PLANTED_SECRET)
    )
    recorder = FakeEventRecorder(error=failure)

    verdict = await _handler(store, ScriptedExecutor(), recorder).handle(run.id)

    assert verdict.kind is VerdictKind.DONE
    assert store.runs[run.id].status.value == "succeeded"


async def test_recorder_timeout_is_bounded() -> None:
    """Scenario: Event storage failures never break generation"""
    recorder = FakeEventRecorder(delay=EVENT_WRITE_TIMEOUT_SECONDS * 5)
    started = time.monotonic()
    async with generation_event_scope(_run(), recorder):
        recorded = await record_generation_event(_event())
    elapsed = time.monotonic() - started

    assert recorded is False
    assert elapsed < EVENT_WRITE_TIMEOUT_SECONDS * 3
    assert recorder.records == []


async def test_scope_waits_for_a_carousel_and_never_buffers_between_runs() -> None:
    """Scenario: A queued carousel has a complete generation timeline"""
    recorder = FakeEventRecorder()
    async with generation_event_scope(_run(None), recorder):
        assert await record_generation_event(_event()) is False
        set_generation_event_project("p-later")
        assert await record_generation_event(_event("run_started")) is True
    assert await record_generation_event(_event("run_succeeded")) is False

    assert len(recorder.records) == 1
    assert recorder.records[0][0].carousel_project_id == "p-later"
    assert recorder.records[0][0].id != recorder.records[0][1].id


async def test_successful_queue_run_records_phase_and_final_events() -> None:
    """Scenario: A queued carousel has a complete generation timeline"""
    store = FakeStore()
    run = store.add(resume_run())
    recorder = FakeEventRecorder()

    verdict = await _handler(store, ScriptedExecutor(), recorder).handle(run.id)

    assert verdict.kind is VerdictKind.DONE
    assert [event.event_type for _, event in recorder.records] == [
        "run_started",
        "phase_started",
        "phase_succeeded",
        "run_succeeded",
    ]
    phase = recorder.records[2][1]
    assert phase.phase == "research"
    assert phase.duration_ms is not None
    assert phase.outcome == "succeeded"


async def test_failed_run_records_safe_error_and_retry() -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    store = FakeStore()
    run = store.add(resume_run())
    recorder = FakeEventRecorder()
    executor = ScriptedExecutor(StepOutcome.DONE, error=TimeoutError(PLANTED_SECRET))

    verdict = await _handler(store, executor, recorder).handle(run.id)

    assert verdict.kind is VerdictKind.RETRY
    retry = recorder.records[-1][1]
    assert retry.event_type == "run_retry"
    assert retry.error_code == "transient"
    assert retry.details["error_type"] == "TimeoutError"
    assert retry.details["delay_seconds"] == 24
    assert PLANTED_SECRET not in json.dumps(retry.details)
    assert recorder.records[-2][1].event_type == "phase_failed"


async def test_fixed_run_project_cannot_be_reassigned() -> None:
    """Scenario: Generation log access is owner and admin only"""
    recorder = FakeEventRecorder()
    async with generation_event_scope(_run("p-owner"), recorder):
        set_generation_event_project("p-other")
        assert await record_generation_event(_event()) is True

    assert recorder.records[0][0].carousel_project_id == "p-owner"


async def test_stale_attempt_records_no_phase_or_run_failure() -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    store = FakeStore()
    run = store.add(resume_run())
    recorder = FakeEventRecorder()
    executor = _FencingExecutor(store)

    verdict = await _handler(store, executor, recorder).handle(run.id)

    assert verdict.kind is VerdictKind.DONE
    event_types = [event.event_type for _, event in recorder.records]
    assert event_types == ["run_started", "phase_started"]
    assert store.waits == []


async def test_manual_kick_records_the_queued_run() -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    store = FakeStore()
    run = store.add(resume_run())
    recorder = FakeEventRecorder()
    dispatcher = Dispatcher(
        DispatcherDependencies(
            store=store,
            queue=FakeQueue(),
            autopilot=FakeActiveAutopilot(),
            notices=FakeNotices(),
            events=recorder,
        )
    )

    assert await dispatcher.kick(run.id) is True
    assert [event.event_type for _, event in recorder.records] == ["run_queued"]
    assert recorder.records[0][1].details.get("job_id") is None


async def test_failed_write_emits_one_safe_warning() -> None:
    """Scenario: Event storage failures never break generation"""
    failure = DBAPIError(
        PLANTED_SQL, {"token": PLANTED_SECRET}, Exception(PLANTED_SECRET)
    )
    recorder = FakeEventRecorder(error=failure)
    with capture_logs() as logs:
        async with generation_event_scope(_run(), recorder):
            assert await record_generation_event(_event()) is False

    assert len(logs) == 1
    entry = logs[0]
    assert entry["event"] == "generation_event_store_failed"
    assert entry["event_type"] == "run_failed"
    assert entry["error_type"] == "DBAPIError"
    assert PLANTED_SECRET not in str(entry)
    assert PLANTED_SQL not in str(entry)
