"""Targeted dispatcher kicks reconcile one run without preempting active work."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from rag_backend.modules.generation_queue.domain.models import (
    GenerationRun,
    GenerationStatus,
)
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeActiveAutopilot,
    FakeNotices,
    FakeQueue,
    FakeStore,
    make_run,
)
from tests.unit.modules.generation_queue.test_generation_executors_ae0522 import (
    _dispatcher,
)


async def test_kick_missing_run_is_an_idempotent_noop() -> None:
    """Scenario: A stale dispatch notice cannot invent a generation run."""
    store, queue = FakeStore(), FakeQueue()
    dispatcher = _dispatcher(store, queue, FakeActiveAutopilot(), FakeNotices())
    assert await dispatcher.kick(uuid4()) is False
    assert queue.kicked == []
    assert queue.enqueued == []


async def test_kick_sets_an_existing_job_id_without_duplicate_enqueue() -> None:
    """Scenario: Missing and existing jobs are reconciled idempotently."""
    store, queue = FakeStore(), FakeQueue()
    run = store.add(make_run(pgq_job_id=None))
    dispatcher = _dispatcher(store, queue, FakeActiveAutopilot(), FakeNotices())
    assert await dispatcher.kick(run.id) is True
    first_job = store.runs[run.id].pgq_job_id
    assert first_job is not None
    assert await dispatcher.kick(run.id) is True
    assert store.runs[run.id].pgq_job_id == first_job
    assert queue.kicked == [run.id, run.id]
    assert queue.enqueued == [run.id]
    assert len(queue.jobs) == 1


async def test_kick_never_replaces_or_cancels_an_active_drive() -> None:
    """Scenario: The active drive is never preempted by a targeted kick."""
    store = FakeStore()
    run = store.add(make_run(status=GenerationStatus.RUNNING, pgq_job_id=7))
    queue = FakeQueue(jobs={run.dedupe_key: 7}, alive={7})
    dispatcher = _dispatcher(store, queue, FakeActiveAutopilot(), FakeNotices())
    assert await dispatcher.kick(run.id) is False
    assert queue.kicked == []
    assert queue.enqueued == []
    assert store.runs[run.id].pgq_job_id == 7
    assert store.runs[run.id].status is GenerationStatus.RUNNING


async def test_kick_does_not_set_a_job_after_the_run_completes() -> None:
    """Scenario: A completion racing a kick leaves the terminal row untouched."""
    store = FakeStore()
    run = store.add(make_run(pgq_job_id=None))

    class _CompletingQueue(FakeQueue):
        async def kick(self, run: GenerationRun) -> int:
            store.runs[run.id] = replace(run, status=GenerationStatus.SUCCEEDED)
            return 9

    queue = _CompletingQueue()
    dispatcher = _dispatcher(store, queue, FakeActiveAutopilot(), FakeNotices())
    assert await dispatcher.kick(run.id) is False
    assert store.runs[run.id].status is GenerationStatus.SUCCEEDED
    assert store.runs[run.id].pgq_job_id is None
