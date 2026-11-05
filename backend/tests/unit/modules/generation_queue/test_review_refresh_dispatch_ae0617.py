"""The dispatcher runs a final-review refresh ahead of queued full drives.

Feature: backend/tests/features/review_refresh_priority_ae0617.feature
"""

from __future__ import annotations

from dataclasses import replace

from rag_backend.modules.generation_queue.bootstrap import _NoAutopilot
from rag_backend.modules.generation_queue.constants import (
    MANUAL_REPROCESS_PRIORITY,
    ORDINARY_PRIORITY,
    REVIEW_REFRESH_PRIORITY,
)
from rag_backend.modules.generation_queue.domain.models import (
    AutopilotDrivePayload,
    GenerationKind,
    GenerationStatus,
    autopilot_stage,
    review_refresh_stage,
)
from rag_backend.modules.generation_queue.domain.priority import priority_of
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

_RUN = "r1"
_PROJECT = "p1"
_KEY = "autopilot:r1"


def _active(*, refresh: bool = True) -> FakeActiveAutopilot:
    """A run in ``reworking``, also listed as a final-review refresh when asked."""
    listed = [(_RUN, _PROJECT)]
    return FakeActiveAutopilot(runs=listed, refreshes=listed if refresh else [])


def test_refresh_shares_the_manual_class() -> None:
    """Scenario: A refresh drive is picked before older ordinary drives"""
    assert REVIEW_REFRESH_PRIORITY == MANUAL_REPROCESS_PRIORITY
    assert REVIEW_REFRESH_PRIORITY > ORDINARY_PRIORITY


def test_refresh_stage_is_an_autopilot_drive_at_the_raised_priority() -> None:
    """Scenario: A refresh drive is picked before older ordinary drives"""
    stage = review_refresh_stage(_RUN, _PROJECT)
    ordinary = autopilot_stage(_RUN, _PROJECT)
    assert priority_of(stage.payload) == REVIEW_REFRESH_PRIORITY
    assert AutopilotDrivePayload.parse(stage.payload).autopilot_run_id == _RUN
    assert stage.kind is GenerationKind.AUTOPILOT_DRIVE
    assert stage.dedupe_key == ordinary.dedupe_key
    assert stage.autopilot_run_id == _RUN
    assert stage.carousel_project_id == _PROJECT


async def test_a_new_refresh_is_staged_raised_once_and_counted_once() -> None:
    """Scenario: A refresh drive is picked before older ordinary drives"""
    store, queue = FakeStore(), FakeQueue()
    dispatcher = _dispatcher(store, queue, _active(), FakeNotices())
    report = await dispatcher.run_once()
    assert report.staged == 1
    assert report.dispatched == 1
    [run] = store.runs.values()
    assert priority_of(run.payload) == REVIEW_REFRESH_PRIORITY
    assert queue.raised == []


async def test_a_waiting_drive_is_raised_on_store_and_queue() -> None:
    """Scenario: A drive staged before the run became a refresh is raised"""
    store, queue = FakeStore(), FakeQueue(jobs={_KEY: 7}, alive={7})
    waiting = store.add(make_run(dedupe_key=_KEY, pgq_job_id=7))
    report = await _dispatcher(store, queue, _active(), FakeNotices()).run_once()
    assert report.staged == 0
    assert priority_of(store.runs[waiting.id].payload) == REVIEW_REFRESH_PRIORITY
    assert store.runs[waiting.id].pgq_job_id == 7
    assert queue.raised == [waiting.id]


async def test_a_drive_in_retry_wait_is_raised() -> None:
    """Scenario: A raised drive waiting for its render keeps its delay"""
    store, queue = FakeStore(), FakeQueue(jobs={_KEY: 7}, alive={7})
    waiting = store.add(
        make_run(dedupe_key=_KEY, pgq_job_id=7, status=GenerationStatus.RETRY_WAIT)
    )
    await _dispatcher(store, queue, _active(), FakeNotices()).run_once()
    assert priority_of(store.runs[waiting.id].payload) == REVIEW_REFRESH_PRIORITY
    assert store.runs[waiting.id].status is GenerationStatus.RETRY_WAIT
    assert queue.raised == [waiting.id]


async def test_a_running_drive_is_left_alone() -> None:
    """Scenario: A refresh drive that is itself running is left alone"""
    store, queue = FakeStore(), FakeQueue(jobs={_KEY: 7}, alive={7})
    running = make_run(dedupe_key=_KEY, pgq_job_id=7, status=GenerationStatus.RUNNING)
    store.add(running)
    await _dispatcher(store, queue, _active(), FakeNotices()).run_once()
    assert priority_of(store.runs[running.id].payload) == ORDINARY_PRIORITY
    assert store.runs[running.id].status is GenerationStatus.RUNNING
    assert queue.raised == []


async def test_a_drive_with_no_job_is_handed_over_raised() -> None:
    """Scenario: A refresh drive with no job yet carries the raised priority"""
    store, queue = FakeStore(), FakeQueue()
    waiting = store.add(make_run(dedupe_key=_KEY, pgq_job_id=None))
    report = await _dispatcher(store, queue, _active(), FakeNotices()).run_once()
    assert queue.raised == []
    assert report.dispatched == 1
    assert queue.enqueued == [waiting.id]
    assert priority_of(store.runs[waiting.id].payload) == REVIEW_REFRESH_PRIORITY


async def test_a_second_pass_changes_nothing() -> None:
    """Scenario: A drive staged before the run became a refresh is raised"""
    store, queue = FakeStore(), FakeQueue(jobs={_KEY: 7}, alive={7})
    waiting = store.add(make_run(dedupe_key=_KEY, pgq_job_id=7))
    dispatcher = _dispatcher(store, queue, _active(), FakeNotices())
    await dispatcher.run_once()
    first = store.runs[waiting.id]
    report = await dispatcher.run_once()
    assert report.staged == 0
    assert store.runs[waiting.id] == replace(first)


async def test_an_ordinary_rework_keeps_fifo() -> None:
    """Scenario Outline: A rework with work left keeps FIFO"""
    store, queue = FakeStore(), FakeQueue()
    report = await _dispatcher(
        store, queue, _active(refresh=False), FakeNotices()
    ).run_once()
    assert report.staged == 1
    [run] = store.runs.values()
    assert priority_of(run.payload) == ORDINARY_PRIORITY
    assert queue.raised == []


async def test_autopilot_off_lists_no_refresh() -> None:
    """Scenario: With autopilot off nothing is raised"""
    assert await _NoAutopilot.review_refresh_run_ids(5) == []
