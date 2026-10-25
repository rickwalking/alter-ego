"""The dashboard's queue panel: the generation queue as Pedro sees it. Pure.

Active runs keep the queue's FIFO order; the running one is first. A queued run's
start estimate is ``now`` plus one average drive per run ahead. Dead letters stay
on the panel while their autopilot run is still parked by the queue; a dashboard
dead letter is shown without buttons (Pedro retries it from the editor).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from rag_backend.modules.autopilot.domain.dead_letter import is_dead_letter
from rag_backend.modules.autopilot.domain.queue_position import average_drive_minutes
from rag_backend.modules.autopilot.queue_constants import (
    AUTOPILOT_STATE_QUEUED,
    BOARD_KIND_AUTOPILOT,
    BOARD_KIND_DASHBOARD,
    GENERATION_KIND_AUTOPILOT,
    GENERATION_STATUS_DEAD,
    GENERATION_STATUS_QUEUED,
    GENERATION_STATUS_RETRY_WAIT,
    GENERATION_STATUS_RUNNING,
)


@dataclass(frozen=True, kw_only=True)
class GenerationRow:
    """One generation run as the queue reports it."""

    id: str
    kind: str
    status: str
    autopilot_run_id: str | None
    carousel_project_id: str | None
    title: str
    last_phase: str | None
    last_error_code: str | None
    created_at: datetime
    started_at: datetime | None
    next_attempt_at: datetime | None
    finished_at: datetime | None
    superseded: bool = False


@dataclass(frozen=True, kw_only=True)
class AutopilotFacts:
    """The theme title and the current reason of one autopilot run."""

    title: str
    state: str
    state_reason: str | None


@dataclass(frozen=True, kw_only=True)
class BoardItem:
    """One row of the panel with the buttons it offers."""

    id: str
    kind: str
    status: str
    title: str
    project_id: str | None
    phase: str | None
    position: int | None
    eta: datetime | None
    started_at: datetime | None
    next_attempt_at: datetime | None
    error_code: str | None
    can_retry: bool
    can_discard: bool
    can_cancel: bool


@dataclass(frozen=True, kw_only=True)
class BacklogItem:
    """A theme waiting in the backlog, with the day it expires."""

    candidate_id: str
    title: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, kw_only=True)
class QueueBoard:
    """The panel: active runs, dead letters, backlog and the average drive time."""

    active: tuple[BoardItem, ...]
    dead: tuple[BoardItem, ...]
    backlog: tuple[BacklogItem, ...]
    average_drive_minutes: float


@dataclass(frozen=True, kw_only=True)
class BoardInputs:
    """What the board is built from."""

    rows: Sequence[GenerationRow]
    facts: Mapping[str, AutopilotFacts]
    backlog: Sequence[BacklogItem]
    drive_minutes: Sequence[float]
    now: datetime


def build_board(inputs: BoardInputs) -> QueueBoard:
    """Order, number and label every row."""
    average = average_drive_minutes(inputs.drive_minutes)
    active_rows = [row for row in inputs.rows if row.status != GENERATION_STATUS_DEAD]
    active_rows.sort(key=_running_first)
    in_line = [row for row in active_rows if row.status != GENERATION_STATUS_RETRY_WAIT]
    places = {row.id: index for index, row in enumerate(in_line)}
    active = tuple(
        _active_item(row, inputs, (places.get(row.id), average)) for row in active_rows
    )
    dead = tuple(
        _dead_item(row, inputs.facts)
        for row in inputs.rows
        if row.status == GENERATION_STATUS_DEAD and _still_parked(row, inputs.facts)
    )
    return QueueBoard(
        active=active,
        dead=dead,
        backlog=tuple(inputs.backlog),
        average_drive_minutes=average,
    )


def _running_first(row: GenerationRow) -> int:
    return 0 if row.status == GENERATION_STATUS_RUNNING else 1


def _active_item(
    row: GenerationRow, inputs: BoardInputs, place: tuple[int | None, float]
) -> BoardItem:
    index, average = place
    autopilot = _is_autopilot(row)
    facts = inputs.facts.get(row.autopilot_run_id or "")
    queued = row.status == GENERATION_STATUS_QUEUED and index is not None
    not_started = facts is not None and facts.state == AUTOPILOT_STATE_QUEUED
    return BoardItem(
        id=row.id,
        kind=BOARD_KIND_AUTOPILOT if autopilot else BOARD_KIND_DASHBOARD,
        status=row.status,
        title=_title(row, facts),
        project_id=row.carousel_project_id,
        phase=row.last_phase,
        position=index + 1 if index is not None else None,
        eta=inputs.now + timedelta(minutes=average * (index or 0)) if queued else None,
        started_at=row.started_at,
        next_attempt_at=row.next_attempt_at,
        error_code=row.last_error_code,
        can_retry=False,
        can_discard=False,
        can_cancel=autopilot
        and not_started
        and row.status in {GENERATION_STATUS_QUEUED, GENERATION_STATUS_RETRY_WAIT},
    )


def _dead_item(row: GenerationRow, facts: Mapping[str, AutopilotFacts]) -> BoardItem:
    autopilot = _is_autopilot(row)
    return BoardItem(
        id=row.id,
        kind=BOARD_KIND_AUTOPILOT if autopilot else BOARD_KIND_DASHBOARD,
        status=row.status,
        title=_title(row, facts.get(row.autopilot_run_id or "")),
        project_id=row.carousel_project_id,
        phase=row.last_phase,
        position=None,
        eta=None,
        started_at=row.started_at,
        next_attempt_at=None,
        error_code=row.last_error_code,
        can_retry=autopilot,
        can_discard=autopilot,
        can_cancel=False,
    )


def _still_parked(row: GenerationRow, facts: Mapping[str, AutopilotFacts]) -> bool:
    """A dashboard dead letter until a later run of its project; an autopilot one
    until it is resolved."""
    if not _is_autopilot(row):
        return not row.superseded
    found = facts.get(row.autopilot_run_id or "")
    return found is not None and is_dead_letter(found.state_reason)


def _is_autopilot(row: GenerationRow) -> bool:
    return row.kind == GENERATION_KIND_AUTOPILOT and row.autopilot_run_id is not None


def _title(row: GenerationRow, facts: AutopilotFacts | None) -> str:
    if facts is not None and facts.title:
        return facts.title
    return row.title


__all__ = [
    "AutopilotFacts",
    "BacklogItem",
    "BoardInputs",
    "BoardItem",
    "GenerationRow",
    "QueueBoard",
    "build_board",
]
