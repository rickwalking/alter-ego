"""Telegram dead-letter retry and discard callback contracts."""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.queue_constants import (
    CALLBACK_DEAD_DISCARD_PREFIX,
    CALLBACK_DEAD_RETRY_PREFIX,
    TEXT_DEAD_DISCARDED,
    TEXT_QUEUE_ALREADY,
)
from tests.unit.modules.autopilot.test_owner_actions import _tap
from tests.unit.modules.autopilot.test_queue_owner_actions_ae0523 import (
    _DEAD,
    _S,
    _handle,
    _run,
    _said,
    _world,
)


@pytest.mark.asyncio
async def test_retry_resumes_an_escalated_dead_letter() -> None:
    """Scenario: Retry resumes a run that died mid-generation"""
    run = _run(_S.ESCALATED, _DEAD)
    world = _world(run)
    await _handle(world, _tap(1, f"{CALLBACK_DEAD_RETRY_PREFIX}{run.run_id}"))
    assert world.runs.runs[run.run_id].state is _S.GENERATING
    assert world.queue.requeued == [run.run_id]
    assert "De volta à fila. Na fila: posição 1 de 1" in _said(world)[-1]


@pytest.mark.asyncio
async def test_retry_restarts_a_failed_dead_letter_as_a_new_run() -> None:
    """Scenario: Retry restarts a run that died before it started"""
    run = _run(_S.FAILED, _DEAD)
    world = _world(run)
    await _handle(world, _tap(1, f"{CALLBACK_DEAD_RETRY_PREFIX}{run.run_id}"))
    assert world.runs.runs[run.run_id].state is _S.FAILED
    assert [c.run_id for c in world.dead.retried] == [run.run_id]
    assert "posição 1 de 1" in _said(world)[-1]


@pytest.mark.asyncio
async def test_retry_happens_once() -> None:
    """Scenario: Retry happens once"""
    escalated = _run(_S.ESCALATED, _DEAD)
    failed = _run(_S.FAILED, _DEAD)
    world = _world(escalated, failed)
    for update_id, run in ((1, escalated), (3, failed)):
        data = f"{CALLBACK_DEAD_RETRY_PREFIX}{run.run_id}"
        await _handle(world, _tap(update_id, data))
        await _handle(world, _tap(update_id + 1, data))
        assert _said(world)[-1] == TEXT_QUEUE_ALREADY
    assert world.queue.requeued == [escalated.run_id]
    assert len(world.dead.retried) == 1


@pytest.mark.asyncio
async def test_retry_is_refused_for_an_engine_error_escalation() -> None:
    """Scenario: Retry is refused for an escalation that is not a queue dead letter"""
    run = _run(_S.ESCALATED, "engine_error:RuntimeError")
    world = _world(run)
    await _handle(world, _tap(1, f"{CALLBACK_DEAD_RETRY_PREFIX}{run.run_id}"))
    assert world.runs.runs[run.run_id].state is _S.ESCALATED
    assert world.queue.requeued == []
    assert _said(world)[-1] == TEXT_QUEUE_ALREADY


@pytest.mark.asyncio
async def test_discard_closes_a_dead_letter() -> None:
    """Scenario: Discard closes a dead-lettered run"""
    escalated = _run(_S.ESCALATED, _DEAD)
    failed = _run(_S.FAILED, _DEAD)
    world = _world(escalated, failed)
    await _handle(world, _tap(1, f"{CALLBACK_DEAD_DISCARD_PREFIX}{escalated.run_id}"))
    await _handle(world, _tap(2, f"{CALLBACK_DEAD_DISCARD_PREFIX}{failed.run_id}"))
    await _handle(world, _tap(3, f"{CALLBACK_DEAD_DISCARD_PREFIX}{failed.run_id}"))
    assert world.runs.runs[escalated.run_id].state is _S.REJECTED
    assert world.dead.discarded == [failed.run_id]
    assert world.queue.requeued == []
    assert _said(world)[-3:] == [
        TEXT_DEAD_DISCARDED,
        TEXT_DEAD_DISCARDED,
        TEXT_QUEUE_ALREADY,
    ]
