"""The dispatcher leaves a requeued dead letter alone when its old held job remains.

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from rag_backend.modules.generation_queue.domain.models import (
    GenerationStatus,
    HeldJob,
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


async def test_a_requeued_dead_letter_is_not_parked_again_by_its_old_job() -> None:
    """Scenario: A requeued dead letter is not parked again by its old held job"""
    store, notices = FakeStore(), FakeNotices()
    requeued = store.add(make_run(status=GenerationStatus.QUEUED, pgq_job_id=None))
    moved_on = store.add(make_run(status=GenerationStatus.RUNNING, pgq_job_id=8))
    queue = FakeQueue(
        alive={8},
        held_jobs=[
            HeldJob(job_id=3, generation_run_id=requeued.id),
            HeldJob(job_id=7, generation_run_id=moved_on.id),
        ],
    )
    report = await _dispatcher(store, queue, FakeActiveAutopilot(), notices).run_once()
    assert report.dead_lettered == 0
    assert notices.staged == []
    assert queue.forgotten == [3, 7]
    assert store.runs[requeued.id].status is GenerationStatus.QUEUED
    assert store.runs[requeued.id].pgq_job_id is not None
    assert store.runs[moved_on.id].status is GenerationStatus.RUNNING
