"""The checklist item repair script: dry run, apply, idempotence and usage.

Feature file: tests/features/carousel_checklist_wysiwyg.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import cast
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.checklist_item_repair import (
    ChecklistItemMove,
    ChecklistRepairPlan,
)
from rag_backend.bootstrap import carousel_checklist_repair as repair
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.scripts.cli_support import EXIT_USAGE
from rag_backend.scripts.repair_checklist_items import format_report, main

_MOVE = ChecklistItemMove(
    slide_index=8,
    locale="pt",
    list_key="summary_points",
    item_index=0,
    old_title="Gerado",
    new_title="Editado",
)


@dataclass
class _Calls:
    edits: list[ChecklistRepairPlan] = field(default_factory=list)
    republished: list[str] = field(default_factory=list)


@asynccontextmanager
async def _session() -> AsyncIterator[object]:
    yield object()


def _loaded(
    moves: tuple[ChecklistItemMove, ...], status: CarouselStatus
) -> repair._Loaded:
    project = CarouselProject(topic="T", audience="A", niche="N")
    project.status = status
    return repair._Loaded(
        project=project,
        lock_version=3,
        plan=ChecklistRepairPlan(moves=moves, edited_slides=[{"slide_index": 8}]),
    )


def _install(
    monkeypatch: pytest.MonkeyPatch,
    loaded: repair._Loaded | None,
    republish_errors: tuple[str, ...] = (),
) -> _Calls:
    calls = _Calls()

    async def load(_db: object, _project_id: object) -> repair._Loaded | None:
        return loaded

    async def edit(_db: object, value: repair._Loaded) -> None:
        calls.edits.append(value.plan)

    async def republish(_maker: object, project_id: str) -> tuple[str, ...]:
        calls.republished.append(project_id)
        return republish_errors

    monkeypatch.setattr(repair, "_load", load)
    monkeypatch.setattr(repair, "_edit", edit)
    monkeypatch.setattr(repair, "_republish", republish)
    return calls


async def _run(*, apply: bool) -> repair.ChecklistRepairReport:
    maker = cast("repair.SessionMaker", _session)
    request = repair.ChecklistRepairRequest(project_id=uuid4(), apply=apply)
    return await repair.repair_checklist_items(maker, request)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dry_run_lists_the_moves_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    calls = _install(monkeypatch, _loaded((_MOVE,), CarouselStatus.COMPLETED))

    report = await _run(apply=False)

    assert report.moves == (_MOVE,)
    assert not report.applied
    assert calls.edits == []
    assert calls.republished == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_edits_through_the_service_and_republishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    calls = _install(monkeypatch, _loaded((_MOVE,), CarouselStatus.COMPLETED))

    report = await _run(apply=True)

    assert report.applied
    assert report.republished
    assert len(calls.edits) == 1
    assert calls.republished == [report.project_id]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_second_apply_finds_nothing_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    calls = _install(monkeypatch, _loaded((), CarouselStatus.COMPLETED))

    report = await _run(apply=True)

    assert report.moves == ()
    assert not report.applied
    assert calls.edits == []
    assert calls.republished == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_refuses_a_carousel_that_is_not_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    calls = _install(monkeypatch, _loaded((_MOVE,), CarouselStatus.FAILED))

    report = await _run(apply=True)

    assert report.errors == (repair.ERR_PROJECT_NOT_COMPLETED,)
    assert calls.edits == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_project_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    _install(monkeypatch, None)

    report = await _run(apply=True)

    assert report.errors == (repair.ERR_PROJECT_NOT_FOUND,)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failed_republish_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    _install(monkeypatch, _loaded((_MOVE,), CarouselStatus.COMPLETED), ("pdf failed",))

    report = await _run(apply=True)

    assert report.applied
    assert not report.republished
    assert report.errors == ("pdf failed",)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_held_lock_is_reported_without_a_republish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    calls = _install(monkeypatch, _loaded((_MOVE,), CarouselStatus.COMPLETED))

    async def held(_db: object, _value: repair._Loaded) -> None:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
        )

    monkeypatch.setattr(repair, "_edit", held)

    report = await _run(apply=True)

    assert report.errors == (CONFLICT_CODE_MUTATION_IN_PROGRESS,)
    assert not report.applied
    assert calls.republished == []


@pytest.mark.unit
def test_report_lines_name_each_move() -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    report = repair.ChecklistRepairReport(project_id="p", moves=(_MOVE,))

    lines = format_report(report)

    assert lines[0].startswith("summary: project=p moves=1 applied=False")
    assert lines[1] == "  slide 8 pt summary_points[0]: 'Gerado' -> 'Editado'"


@pytest.mark.unit
def test_project_must_be_a_uuid(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: A repair moves hidden checklist text into the displayed line."""
    assert main(["--project", "not-a-uuid"]) == EXIT_USAGE
    assert "--project must be a carousel UUID" in capsys.readouterr().err
