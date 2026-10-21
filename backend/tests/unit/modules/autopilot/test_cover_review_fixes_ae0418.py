"""PR #136 review fixes: shared cover images and a failed re-render.

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario: Sweeping an unused cover keeps a used cover with the same bytes
  Scenario: A failed slide-1 re-render is escalated, never reported as done
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.application.cover_sweep import (
    CoverSweepDependencies,
    CoverSweepService,
)
from rag_backend.modules.autopilot.constants import GATE_FINAL_REVIEW
from rag_backend.modules.autopilot.cover_constants import (
    REASON_COVER_RENDER_FAILED,
    TEXT_COVER_RENDER_FAILED,
)
from rag_backend.modules.autopilot.domain.cover_ports import CoverSwitchStatus
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.pov_constants import POV_TEXT_BY_REASON
from tests.unit.modules.autopilot.test_autopilot_runner import _Editorial
from tests.unit.modules.autopilot.test_cover_flow_ae0418 import (
    _Clock,
    _Covers,
    _Images,
    _Offers,
    _reworking,
    _runner,
    _stored,
    _Switcher,
)

_S = AutopilotRunState


@pytest.mark.unit
class TestSharedImageSweep:
    # Scenario: Sweeping an unused cover keeps a used cover with the same bytes
    @pytest.mark.asyncio
    async def test_image_another_cover_uses_is_kept(self) -> None:
        unused = _stored(7)
        used = replace(
            _stored(7),
            creator_asset_id=unused.creator_asset_id,
            topic_candidate_id=uuid4(),
        )
        lone = _stored(8)
        covers = _Covers(
            stored={c.asset_id: c for c in (unused, used, lone)},
        )
        images = _Images()
        sweep = CoverSweepService(
            CoverSweepDependencies(covers=covers, images=images, clock=_Clock())
        )
        assert await sweep.tick() == 2
        assert sorted(map(str, covers.deleted)) == sorted([
            str(unused.asset_id),
            str(lone.asset_id),
        ])
        assert images.deleted == [lone.creator_asset_id]

    @pytest.mark.asyncio
    async def test_two_expired_covers_of_one_image_delete_it_once(self) -> None:
        first = _stored(7)
        second = replace(_stored(7), creator_asset_id=first.creator_asset_id)
        covers = _Covers(stored={c.asset_id: c for c in (first, second)})
        images = _Images()
        sweep = CoverSweepService(
            CoverSweepDependencies(covers=covers, images=images, clock=_Clock())
        )
        assert await sweep.tick() == 2
        assert images.deleted == [first.creator_asset_id]


@pytest.mark.unit
class TestRenderFailure:
    # Scenario: A failed slide-1 re-render is escalated, never reported as done
    @pytest.mark.asyncio
    async def test_failed_render_escalates_and_clears_the_rework(self) -> None:
        runs = _reworking()
        switcher = _Switcher(status=CoverSwitchStatus.RENDER_FAILED)
        runner, _notices = _runner(
            runs, _Editorial(phase=GATE_FINAL_REVIEW), _Offers(), switcher
        )
        assert await runner.tick() == 1
        assert len(switcher.commands) == 1
        assert runs.run.state is _S.ESCALATED
        assert runs.run.state_reason == REASON_COVER_RENDER_FAILED
        assert runs.run.rework_phase is None
        assert runs.run.escalated_version == 4

    def test_the_owner_is_told_in_plain_words(self) -> None:
        assert POV_TEXT_BY_REASON[REASON_COVER_RENDER_FAILED] == (
            TEXT_COVER_RENDER_FAILED
        )
