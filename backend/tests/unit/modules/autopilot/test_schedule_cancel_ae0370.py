"""Cancel, publish now while scheduled, next_slot mode, and safety (AE-0370).

Gherkin: tests/features/autopilot_scheduled_publish.feature
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.modules.autopilot.domain.messages import review_keyboard
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.schedule import local_label
from rag_backend.modules.autopilot.domain.schedule_keyboards import (
    scheduled_keyboard,
)
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_OWNER_PUBLISH_NOW,
    REASON_OWNER_UNSCHEDULED,
    TEXT_UNSCHEDULED,
)
from rag_backend.modules.autopilot.webhook_constants import (
    ANSWER_ALREADY,
    TEXT_ALREADY,
    TEXT_APPROVE_FAILED,
)
from rag_backend.modules.editorial.public import WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
from tests.unit.modules.autopilot.test_owner_actions import _PROJECT, _STRANGER, _tap
from tests.unit.modules.autopilot.test_schedule_webhook_ae0370 import (
    _handle,
    _local,
    _schedule_slot,
    _world,
)

_S = AutopilotRunState


# Scenario: Cancel returns the run to the review
@pytest.mark.asyncio
async def test_cancel_returns_to_the_review() -> None:
    world = _world()
    await _schedule_slot(world, _local(15, 18))
    await _handle(world, _tap(2, world.data("unsched")))
    run = world.runs.run
    assert run.state is _S.AWAITING_OWNER
    assert run.state_reason == REASON_OWNER_UNSCHEDULED
    assert run.scheduled_at is None
    edit = world.messenger.edits[-1]
    assert edit.text == TEXT_UNSCHEDULED
    assert edit.keyboard == review_keyboard(world.run_id)
    await _handle(world, _tap(3, world.data("unsched")))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY


@pytest.mark.asyncio
async def test_publish_now_after_cancel_does_not_approve_twice() -> None:
    world = _world()
    await _schedule_slot(world, _local(15, 18))
    world.carousels.workflow_status = WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
    await _handle(world, _tap(2, world.data("unsched")))
    await _handle(world, _tap(3, world.data("pubnow")))
    assert len(world.editorial.resumes) == 1
    assert world.runs.run.state is _S.PUBLISHING
    assert world.release.ids == [_PROJECT]


# Scenario: Publish now while scheduled publishes immediately
@pytest.mark.asyncio
async def test_publish_now_while_scheduled() -> None:
    world = _world()
    await _schedule_slot(world, _local(15, 18))
    await _handle(world, _tap(2, world.data("pubnow")))
    run = world.runs.run
    assert run.state is _S.PUBLISHING
    assert run.state_reason == REASON_OWNER_PUBLISH_NOW
    assert run.scheduled_at is None
    assert world.release.ids == [_PROJECT]
    assert len(world.editorial.resumes) == 1
    await _handle(world, _tap(3, world.data("pubnow")))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY


@pytest.mark.asyncio
async def test_publish_now_while_scheduled_with_missing_carousel_fails() -> None:
    world = _world()
    await _schedule_slot(world, _local(15, 18))
    world.release.ok = False
    await _handle(world, _tap(2, world.data("pubnow")))
    assert world.runs.run.state is _S.PUBLISH_FAILED
    assert world.messenger.edits[-1].text == TEXT_APPROVE_FAILED


# Scenario: next_slot mode schedules the next slot directly
@pytest.mark.asyncio
async def test_next_slot_mode_schedules_on_approve() -> None:
    world = _world(default_publish="next_slot")
    await _handle(world, _tap(1, world.data("approve")))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.scheduled_at == _local(15, 12)
    edit = world.messenger.edits[-1]
    assert edit.text.startswith("\U0001f5d3 Agendado para 15/10 12:00")
    assert edit.keyboard == scheduled_keyboard(world.run_id)
    assert world.release.ids == []


# Scenario: A non-owner cannot schedule or cancel
@pytest.mark.asyncio
async def test_stranger_cannot_schedule_or_cancel() -> None:
    world = _world()
    await _handle(world, _tap(1, world.slot(_local(15, 18)), actor=_STRANGER))
    assert world.runs.run.state is _S.AWAITING_OWNER
    world.runs.run = replace(world.runs.run, state=_S.SCHEDULED)
    await _handle(world, _tap(2, world.data("unsched"), actor=_STRANGER))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.messenger.answers == []
    assert world.messenger.edits == []
    assert world.editorial.resumes == []


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["approve", "sched", "other", "pubnow"])
async def test_buttons_on_a_moved_run_are_already_handled(kind: str) -> None:
    world = _world(state=_S.PUBLISHED)
    await _handle(world, _tap(1, world.data(kind)))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY
    assert world.messenger.edits[-1].text == TEXT_ALREADY
    assert world.runs.run.state is _S.PUBLISHED


@pytest.mark.asyncio
async def test_slot_on_a_moved_run_is_already_handled() -> None:
    world = _world(state=_S.REJECTED)
    await _schedule_slot(world, _local(15, 18))
    assert world.messenger.answers[-1].text == ANSWER_ALREADY
    assert world.runs.run.state is _S.REJECTED


def test_local_label_of_the_scheduled_time() -> None:
    assert local_label(_local(15, 18)) == "15/10 18:00"
