"""The remembered autopilot cover the drive asks for at each gate.

Gherkin: tests/features/autopilot_cover_gate_select_ae0615.feature
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    CoverBaseline,
)
from rag_backend.domain.constants.cover_autoselect import (
    OUTCOME_AUTO_SELECT_ALREADY,
    REASON_AUTO_SELECT_COMPLETED,
    REASON_AUTO_SELECT_CONFLICT,
    REASON_AUTO_SELECT_TIMED_OUT,
)
from rag_backend.domain.models.cover_generation import CoverGenerationStatus
from rag_backend.modules.editorial.infrastructure import carousel_cover_gate_select
from rag_backend.modules.editorial.infrastructure.carousel_cover_gate_select import (
    select_cover_at_gate,
)

_BASELINE = CoverBaseline(slide_cover_asset_id=None, hook_asset_id=None)


def _selection(project_id: str = "p-1") -> AutoCoverSelection:
    return AutoCoverSelection(
        project_id=project_id, generation_id=uuid4(), baseline=_BASELINE
    )


@pytest.fixture
def pending() -> Iterator[dict[str, AutoCoverSelection]]:
    remembered = carousel_cover_gate_select._pending
    remembered.clear()
    yield remembered
    remembered.clear()


@pytest.mark.unit
class TestSettle:
    # Scenario: A conflict at the gate is tried again at the next gate
    @pytest.mark.parametrize(
        "outcome", [REASON_AUTO_SELECT_CONFLICT, REASON_AUTO_SELECT_TIMED_OUT]
    )
    def test_retried_outcomes_keep_it(
        self, pending: dict[str, AutoCoverSelection], outcome: str
    ) -> None:
        selection = _selection()
        pending[selection.project_id] = selection

        carousel_cover_gate_select._settle(selection, outcome)

        assert pending == {selection.project_id: selection}

    # Scenario: The drive stores the cover at a gate before it resumes
    @pytest.mark.parametrize(
        "outcome", [OUTCOME_AUTO_SELECT_ALREADY, REASON_AUTO_SELECT_COMPLETED]
    )
    def test_other_outcomes_forget_it(
        self, pending: dict[str, AutoCoverSelection], outcome: str
    ) -> None:
        selection = _selection()
        pending[selection.project_id] = selection

        carousel_cover_gate_select._settle(selection, outcome)

        assert pending == {}

    # Scenario: The drive stores the cover at a gate before it resumes
    def test_a_newer_generation_of_the_carousel_is_kept(
        self, pending: dict[str, AutoCoverSelection]
    ) -> None:
        older, newer = _selection(), _selection()
        pending[newer.project_id] = newer

        carousel_cover_gate_select._settle(older, REASON_AUTO_SELECT_COMPLETED)

        assert pending == {newer.project_id: newer}


@pytest.mark.unit
class TestGate:
    # Scenario: A failed generation leaves slide 1 alone
    @pytest.mark.asyncio
    async def test_nothing_remembered_selects_nothing(
        self, pending: dict[str, AutoCoverSelection]
    ) -> None:
        assert await select_cover_at_gate("p-1") is False
        assert pending == {}

    # Scenario: A failed generation leaves slide 1 alone
    @pytest.mark.asyncio
    async def test_failed_run_is_never_remembered(
        self, pending: dict[str, AutoCoverSelection], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _failed() -> CoverGenerationStatus:
            return CoverGenerationStatus.FAILED

        monkeypatch.setattr(
            carousel_cover_gate_select, "cover_generation_task", lambda _w, _r: _failed
        )
        monkeypatch.setattr(
            carousel_cover_gate_select,
            "cover_selection",
            lambda _run, _project: _selection(),
        )
        task = carousel_cover_gate_select.remembering_cover_task(
            object(), object(), object()
        )

        assert await task() is CoverGenerationStatus.FAILED
        assert pending == {}
