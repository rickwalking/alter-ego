"""POV slots in AE-0370's publish choice (AE-0377, roadmap R6).

Gherkin: tests/features/autopilot_pov_thesis.feature (POV slots wired section)
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.pov_schedule import (
    publish_slots_for,
    run_content_mode,
)
from tests.unit.modules.autopilot.test_owner_actions import _tap
from tests.unit.modules.autopilot.test_schedule_webhook_ae0370 import (
    _handle,
    _local,
    _World,
    _world,
)

_S = AutopilotRunState
_THESIS = "A IA escreve código; decidir o que construir continua sendo do dev."
# Thursday 2026-10-15 13:00 São Paulo: today's noon slot has passed.
_THU_1PM = _local(15, 13)
_OTHER = "✏️ Outro horário"


def _pov(world: _World) -> _World:
    world.runs.run = replace(world.runs.run, pov_thesis=_THESIS)
    world.clock.at = _THU_1PM
    return world


def _menu_labels(world: _World) -> list[str]:
    keyboard = world.messenger.edits[-1].keyboard
    assert keyboard is not None
    return [row[0].text for row in keyboard.rows]


# Scenario: next_slot mode schedules a POV run for Tuesday or Thursday at noon
@pytest.mark.asyncio
async def test_next_slot_mode_schedules_pov_on_tuesday_noon() -> None:
    world = _pov(_world(default_publish="next_slot"))
    await _handle(world, _tap(1, world.data("approve")))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.scheduled_at == _local(20, 12)
    assert world.messenger.edits[-1].text.startswith(
        "\U0001f5d3 Agendado para 20/10 12:00"
    )
    assert world.release.ids == []


# Scenario: The Agendar menu lists the POV slot first
@pytest.mark.asyncio
async def test_schedule_menu_lists_the_pov_slot_first() -> None:
    world = _pov(_world())
    await _handle(world, _tap(1, world.data("sched")))
    assert _menu_labels(world) == ["20/10 12:00", "hoje 18:00", "hoje 21:00", _OTHER]


# Scenario: A Radar IA run keeps the default slots
@pytest.mark.asyncio
async def test_radar_ia_run_keeps_the_default_slots() -> None:
    world = _world()
    world.clock.at = _THU_1PM
    await _handle(world, _tap(1, world.data("sched")))
    assert _menu_labels(world) == ["hoje 18:00", "hoje 21:00", "amanhã 12:00", _OTHER]


@pytest.mark.unit
class TestPublishSlotsFor:
    def test_mode_comes_from_the_confirmed_thesis(self) -> None:
        run = _world().runs.run
        assert run_content_mode(run) is None
        assert run_content_mode(replace(run, pov_thesis="")) is None
        assert run_content_mode(replace(run, pov_thesis=_THESIS)) == "pov"

    def test_pov_slot_equal_to_a_default_slot_is_not_repeated(self) -> None:
        run = replace(_world().runs.run, pov_thesis=_THESIS)
        # Thursday 10:00: the POV slot is today 12:00, also the first default.
        slots = publish_slots_for(run, _local(15, 10))
        assert slots == (_local(15, 12), _local(15, 18), _local(15, 21))

    def test_radar_ia_slots_are_unchanged(self) -> None:
        run = _world().runs.run
        slots = publish_slots_for(run, _THU_1PM)
        assert slots == (_local(15, 18), _local(15, 21), _local(16, 12))
