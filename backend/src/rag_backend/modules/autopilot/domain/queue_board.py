"""Pure dashboard queue rows built from the shared position/ETA core."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from rag_backend.modules.autopilot.domain.dead_letter import is_dead_letter
from rag_backend.modules.autopilot.domain.queue_position import (
    QueueEntry,
    QueuePlacement,
    QueueSnapshot,
    average_drive_minutes,
    queue_placements,
)
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
class GenerationRow(QueueEntry):
    """One staged or synthetic generation row with safe panel capabilities."""

    kind: str
    carousel_project_id: str | None
    title: str
    last_phase: str | None
    last_error_code: str | None
    finished_at: datetime | None
    run_heartbeat_at: datetime | None = None
    lock_version: int | None = None
    can_reprocess: bool = False
    refusal_code: str | None = None
    stuck_kind: str | None = None
    superseded: bool = False


@dataclass(frozen=True, kw_only=True)
class AutopilotFacts:
    """The theme title and the current reason of one autopilot run."""

    title: str
    state: str
    state_reason: str | None


@dataclass(frozen=True, kw_only=True)
class BoardItem:
    """One API row with liveness, identity, priority and permitted actions."""

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
    run_heartbeat_at: datetime | None
    lock_version: int | None
    error_code: str | None
    staged: bool
    autopilot_run_id: str | None
    priority: int
    can_reprocess: bool
    refusal_code: str | None
    stuck_kind: str | None
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


class _ItemState(TypedDict):
    position: int | None
    eta: datetime | None
    next_attempt_at: datetime | None
    run_heartbeat_at: datetime | None
    can_retry: bool
    can_discard: bool
    can_cancel: bool


class _ItemBase(TypedDict):
    id: str
    kind: str
    status: str
    title: str
    project_id: str | None
    phase: str | None
    started_at: datetime | None
    lock_version: int | None
    error_code: str | None
    staged: bool
    autopilot_run_id: str | None
    priority: int
    can_reprocess: bool
    refusal_code: str | None
    stuck_kind: str | None


def build_board(inputs: BoardInputs) -> QueueBoard:
    """Order active rows with the Telegram core and retain parked dead letters."""
    rows = {row.id: row for row in inputs.rows if row.status != GENERATION_STATUS_DEAD}
    snapshot = QueueSnapshot(
        entries=tuple(rows.values()), drive_minutes=tuple(inputs.drive_minutes)
    )
    placements = queue_placements(snapshot, inputs.now)
    active = _active_items(rows, inputs.facts, placements)
    dead = tuple(
        _dead_item(row, inputs.facts)
        for row in inputs.rows
        if row.status == GENERATION_STATUS_DEAD and _still_parked(row, inputs.facts)
    )
    return QueueBoard(
        active=active,
        dead=dead,
        backlog=tuple(inputs.backlog),
        average_drive_minutes=average_drive_minutes(inputs.drive_minutes),
    )


def _active_items(
    rows: dict[str, GenerationRow],
    facts: Mapping[str, AutopilotFacts],
    placements: tuple[QueuePlacement, ...],
) -> tuple[BoardItem, ...]:
    return tuple(
        _active_item(rows[place.entry.id], facts, place) for place in placements
    )


def _active_item(
    row: GenerationRow,
    facts: Mapping[str, AutopilotFacts],
    place: QueuePlacement,
) -> BoardItem:
    found = facts.get(row.autopilot_run_id or "")
    state = _active_state(row, found, place)
    return _item(row, _title(row, found), state)


def _active_state(
    row: GenerationRow, facts: AutopilotFacts | None, place: QueuePlacement
) -> _ItemState:
    not_started = facts is not None and facts.state == AUTOPILOT_STATE_QUEUED
    cancellable = row.status in {GENERATION_STATUS_QUEUED, GENERATION_STATUS_RETRY_WAIT}
    return _ItemState(
        position=place.position,
        eta=place.eta if row.status == GENERATION_STATUS_QUEUED else None,
        next_attempt_at=row.next_attempt_at,
        run_heartbeat_at=_heartbeat(row),
        can_retry=False,
        can_discard=False,
        can_cancel=row.staged and _is_autopilot(row) and not_started and cancellable,
    )


def _dead_item(row: GenerationRow, facts: Mapping[str, AutopilotFacts]) -> BoardItem:
    found = facts.get(row.autopilot_run_id or "")
    allowed = row.staged and _is_autopilot(row)
    state = _ItemState(
        position=None,
        eta=None,
        next_attempt_at=None,
        run_heartbeat_at=None,
        can_retry=allowed,
        can_discard=allowed,
        can_cancel=False,
    )
    return _item(row, _title(row, found), state)


def _item(row: GenerationRow, title: str, state: _ItemState) -> BoardItem:
    kind = BOARD_KIND_AUTOPILOT if _is_autopilot(row) else BOARD_KIND_DASHBOARD
    return BoardItem(**_base(row, title, kind), **state)


def _base(row: GenerationRow, title: str, kind: str) -> _ItemBase:
    return {
        "id": row.id,
        "kind": kind,
        "status": row.status,
        "title": title,
        "project_id": row.carousel_project_id,
        "phase": row.last_phase,
        "started_at": row.started_at,
        "lock_version": row.lock_version,
        "error_code": row.last_error_code,
        "staged": row.staged,
        "autopilot_run_id": row.autopilot_run_id,
        "priority": row.priority,
        "can_reprocess": row.can_reprocess,
        "refusal_code": row.refusal_code,
        "stuck_kind": row.stuck_kind,
    }


def _heartbeat(row: GenerationRow) -> datetime | None:
    if row.status != GENERATION_STATUS_RUNNING:
        return None
    return row.run_heartbeat_at


def _still_parked(row: GenerationRow, facts: Mapping[str, AutopilotFacts]) -> bool:
    """Hide superseded dashboard rows and resolved autopilot dead letters."""
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
