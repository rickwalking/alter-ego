"""The drive's gate selection reads the autopilot cover from the database.

Gherkin: tests/features/autopilot_cover_gate_select_ae0615.feature
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    AutoCoverSelector,
    CoverBaseline,
)
from rag_backend.domain.constants.cover_autoselect import (
    OUTCOME_AUTO_SELECT_ALREADY,
    OUTCOME_AUTO_SELECT_SELECTED,
    REASON_AUTO_SELECT_CONFLICT,
)
from rag_backend.modules.editorial.infrastructure import carousel_cover_gate_select
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    SessionFactory,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_gate_select import (
    select_cover_at_gate,
)

_SELECTION = AutoCoverSelection(
    project_id="p-1",
    generation_id=uuid4(),
    baseline=CoverBaseline(slide_cover_asset_id=None, hook_asset_id=None),
)


def _found(
    selection: AutoCoverSelection | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _lookup(
        _sessions: SessionFactory, _project_id: str
    ) -> AutoCoverSelection | None:
        return selection

    monkeypatch.setattr(carousel_cover_gate_select, "_autopilot_selection", _lookup)


def _outcome(outcome: str, monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waits: list[float] = []

    async def _select(self: AutoCoverSelector, _selection: AutoCoverSelection) -> str:
        waits.append(self._polling.max_wait_seconds)
        return outcome

    monkeypatch.setattr(AutoCoverSelector, "select", _select)
    return waits


@pytest.mark.unit
class TestSelectCoverAtGate:
    # Scenario: A failed generation leaves slide 1 alone
    @pytest.mark.asyncio
    async def test_no_succeeded_autopilot_generation_selects_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _found(None, monkeypatch)
        waits = _outcome(OUTCOME_AUTO_SELECT_SELECTED, monkeypatch)

        assert await select_cover_at_gate(_no_sessions, "p-1") is False
        assert waits == []

    # Scenario: The drive stores the cover at a gate before it resumes
    @pytest.mark.asyncio
    async def test_a_stored_cover_is_reported_without_waiting(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _found(_SELECTION, monkeypatch)
        waits = _outcome(OUTCOME_AUTO_SELECT_SELECTED, monkeypatch)

        assert await select_cover_at_gate(_no_sessions, "p-1") is True
        assert waits == [0.0]

    # Scenario: A conflict at the gate is tried again at the next gate
    @pytest.mark.parametrize(
        "outcome", [OUTCOME_AUTO_SELECT_ALREADY, REASON_AUTO_SELECT_CONFLICT]
    )
    @pytest.mark.asyncio
    async def test_other_outcomes_report_nothing_stored(
        self, monkeypatch: pytest.MonkeyPatch, outcome: str
    ) -> None:
        _found(_SELECTION, monkeypatch)
        _outcome(outcome, monkeypatch)

        assert await select_cover_at_gate(_no_sessions, "p-1") is False


def _no_sessions() -> AsyncSession:
    raise AssertionError("the lookup and the selector are faked")
