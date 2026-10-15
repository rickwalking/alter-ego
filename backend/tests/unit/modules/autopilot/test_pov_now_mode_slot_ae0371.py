"""POV runs land on Tue/Thu 12:00 even in ``now`` mode (PR #106 review, item 5).

Gherkin: tests/features/autopilot_pov_thesis.feature
(POV approve in "now" mode section)
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import pytest

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.schedule_constants import TEXT_PUBLISH_CHOICE
from tests.unit.modules.autopilot.test_owner_actions import _tap
from tests.unit.modules.autopilot.test_schedule_webhook_ae0370 import (
    _handle,
    _PROJECT,
    _local,
    _World,
    _world,
)

_S = AutopilotRunState
_THESIS = "A IA escreve código; decidir o que construir continua sendo do dev."


def _pov_at(moment: datetime) -> _World:
    world = _world(default_publish="now")
    world.runs.run = replace(world.runs.run, pov_thesis=_THESIS)
    world.clock.at = moment
    return world


async def _approve(world: _World) -> None:
    await _handle(world, _tap(1, world.data("approve")))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("approved_at", "expected_slot"),
    [
        # Scenario: approve on Monday → Tuesday 12:00
        (_local(12, 9), _local(13, 12)),
        # Scenario: approve Tuesday 11:50 → Thursday (under 15 minutes ahead)
        (_local(13, 11, 50), _local(15, 12)),
        # Scenario: approve Thursday 13:00 → next Tuesday
        (_local(15, 13), _local(20, 12)),
    ],
)
async def test_pov_approve_in_now_mode_schedules_the_next_pov_slot(
    approved_at: datetime, expected_slot: datetime
) -> None:
    world = _pov_at(approved_at)
    await _approve(world)
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.scheduled_at == expected_slot
    assert world.release.ids == []


# Scenario: a Radar IA approve in "now" mode still publishes now
@pytest.mark.asyncio
async def test_radar_ia_approve_in_now_mode_publishes_now() -> None:
    world = _world(default_publish="now")
    world.clock.at = _local(12, 9)
    await _approve(world)
    assert world.runs.run.state is _S.AWAITING_OWNER
    assert world.runs.run.scheduled_at is None
    assert world.messenger.edits[-1].text == TEXT_PUBLISH_CHOICE

    await _handle(world, _tap(2, world.data("pubnow")))
    assert world.release.ids == [_PROJECT]
    assert world.runs.run.state is _S.PUBLISHING
