"""Shared Postgres helpers of the AE-0615 gate-selection tests.

Feature: tests/features/autopilot_cover_gate_select_ae0615.feature. ``_Drive``
is the autopilot drive between two polls of the background selection: it
passes every gate (the scheduler's ``apply_cover`` at each one, as the runner
calls it) and lands in the final review, so the poll never sees a pause, as in
production.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverPolling,
    AutoCoverSelector,
)
from rag_backend.domain.constants.cover_autoselect import LOG_COVER_AUTO_SELECT
from rag_backend.domain.models.cover_generation import CoverGenerationStatus
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.infrastructure.cover_autostart import (
    EditorialAutoCoverScheduler,
)
from rag_backend.modules.editorial.infrastructure import carousel_cover_autoselect
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    EditorialAutoCoverStore,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_lock import (
    carousel_project_lock,
)
from tests.integration.test_autopilot_cover_autoselect_pg_ae0590 import _seed

RowValues = dict[str, str | int | dict[str, str]]

Task = Callable[[], Awaitable[CoverGenerationStatus]]

_GATES = ("research", "outline", "content", "design", "images")
_NEXT = {
    "research": "outline",
    "outline": "content",
    "content": "design",
    "design": "images",
}
_FINAL_REVIEW = {
    "current_phase": "final_review",
    "phase_status": "awaiting_human",
    "status": "completed",
}


async def _set(engine: AsyncEngine, project_id: str, values: RowValues) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(**values)
        )
        await session.commit()


@dataclass
class _Drive:
    """The autopilot drive between two polls: every gate, then the final review.

    ``before`` runs first (an owner write); ``at_gate`` wraps each gate's
    ``apply_cover`` (a held lock). ``applied`` records each gate's answer.
    """

    engine: AsyncEngine
    project_id: str
    consent: bool = True
    before: RowValues = field(default_factory=dict)
    held_at: frozenset[str] = frozenset()
    applied: list[tuple[str, bool]] = field(default_factory=list)
    ran: bool = False

    def scheduler(self) -> EditorialAutoCoverScheduler:
        factory = async_sessionmaker(self.engine, expire_on_commit=False)
        return EditorialAutoCoverScheduler(factory, consent=self.consent)

    async def sleep(self, _seconds: float) -> None:
        if self.ran:
            return
        self.ran = True
        if self.before:
            await _set(self.engine, self.project_id, self.before)
        for gate in _GATES:
            await self.gate(gate)
        await _set(self.engine, self.project_id, _FINAL_REVIEW)

    async def gate(self, gate: str) -> None:
        """Pause at ``gate``, ask for the cover as the runner does, then resume."""
        await _set(
            self.engine,
            self.project_id,
            {"current_phase": gate, "phase_status": "awaiting_human"},
        )
        applied = await self._apply(gate)
        self.applied.append((gate, applied))
        following = _NEXT.get(gate)
        if following is not None:
            await _set(
                self.engine,
                self.project_id,
                {"current_phase": following, "phase_status": "in_progress"},
            )

    async def _apply(self, gate: str) -> bool:
        if gate not in self.held_at:
            return await self.scheduler().apply_cover(self.project_id)
        async with carousel_project_lock(self.engine, self.project_id, blocking=False):
            return await self.scheduler().apply_cover(self.project_id)


def _poll_through(monkeypatch: pytest.MonkeyPatch, drive: _Drive) -> None:
    """The background selection polls with ``drive.sleep`` between its reads."""
    factory = async_sessionmaker(drive.engine, expire_on_commit=False)

    def _selector() -> AutoCoverSelector:
        return AutoCoverSelector(
            EditorialAutoCoverStore(factory), AutoCoverPolling(sleep=drive.sleep)
        )

    monkeypatch.setattr(carousel_cover_autoselect, "auto_cover_selector", _selector)


async def _running_research(engine: AsyncEngine, dirs: Path) -> tuple[str, list[str]]:
    """The seeded carousel while research runs (the cover's scheduling time)."""
    project_id, photos = await _seed(engine, dirs)
    await _set(
        engine,
        project_id,
        {"current_phase": "research", "phase_status": "in_progress"},
    )
    return project_id, photos


def _reasons(logs: Iterable[Mapping[str, str]]) -> list[str]:
    """The ``reason`` of every cover selection log line, in order."""
    return [e.get("reason", "") for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]
