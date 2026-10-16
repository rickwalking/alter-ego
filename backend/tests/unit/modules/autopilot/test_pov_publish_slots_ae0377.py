"""POV slots in AE-0370's publish choice (AE-0377, roadmap R6).

Gherkin: tests/features/autopilot_pov_thesis.feature (POV slots wired section)
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.pov_schedule import run_content_mode
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


def _pov(world: _World) -> _World:
    world.runs.run = replace(world.runs.run, pov_thesis=_THESIS)
    world.clock.at = _THU_1PM
    return world


def _menu_labels(world: _World) -> list[str]:
    keyboard = world.messenger.edits[-1].keyboard
    assert keyboard is not None
    return [button.text for row in keyboard.rows for button in row]


# Scenario: next_slot mode schedules a POV run for Tuesday or Thursday at noon
@pytest.mark.asyncio
async def test_next_slot_mode_schedules_pov_on_tuesday_noon() -> None:
    world = _pov(_world(default_publish="next_slot"))
    await _handle(world, _tap(1, world.data("approve")))
    assert world.runs.run.state is _S.SCHEDULED
    assert world.runs.run.scheduled_at == _local(20, 12)
    assert world.messenger.edits[-1].text == (
        "\U0001f5d3 Agendado para Ter 20/10 12:00 (padrão do plano POV)"
    )
    assert world.release.ids == []


# Scenario: The Agendar day step stars the POV day (AE-0404)
@pytest.mark.asyncio
async def test_schedule_menu_stars_the_pov_day() -> None:
    world = _pov(_world())
    await _handle(world, _tap(1, world.data("sched")))
    assert _menu_labels(world) == [
        "Qui 15/10",
        "Sex 16/10",
        "Sáb 17/10",
        "Dom 18/10",
        "Seg 19/10",
        "Ter 20/10 ⭐",
        "Qua 21/10",
    ]


# Scenario: A Radar IA run keeps the default slots (no starred day)
@pytest.mark.asyncio
async def test_radar_ia_run_stars_no_day() -> None:
    world = _world()
    world.clock.at = _THU_1PM
    await _handle(world, _tap(1, world.data("sched")))
    labels = _menu_labels(world)
    assert labels[0] == "Qui 15/10"
    assert all("⭐" not in label for label in labels)


@pytest.mark.unit
class TestRunContentMode:
    def test_mode_comes_from_the_confirmed_thesis(self) -> None:
        run = _world().runs.run
        assert run_content_mode(run) is None
        assert run_content_mode(replace(run, pov_thesis="")) is None
        assert run_content_mode(replace(run, pov_thesis=_THESIS)) == "pov"
