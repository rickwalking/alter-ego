"""Signed-off, keep-latest prune of old carousel checkpoints.

A thread is eligible when its carousel project is finished (completed or
failed), was last updated before the cutoff, is not running, has no pending
republish, has no autopilot run that is not settled (queued, generating, waiting
for the owner, reworking, scheduled, publishing, or held after a failure), and
was rejected or published. Threads without a carousel project are never
eligible: they may belong to another graph. Each pruned thread keeps its latest
checkpoint, so a run that resumes it later still has its node-level state.

``find_candidates`` only reads. ``apply_prune`` locks the eligible projects,
refuses when a signed-off thread is no longer eligible, writes every prunable row
to the backup file (created owner-only, never overwritten) and checks it, then
deletes in the same transaction. If the delete then rolls back, the backup lists
rows that are still in the tables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import structlog
from sqlalchemy import Select, column, exists, literal, or_, select, table
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from rag_backend.domain.carousel_checkpoint_thread import checkpoint_thread_id
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_REJECTED,
)
from rag_backend.domain.constants.checkpoint_prune import (
    AUTOPILOT_RUNS_TABLE,
    AUTOPILOT_SETTLED_STATES,
    ERR_BACKUP_MISMATCH,
    ERR_NO_THREADS,
    ERR_NOOP,
    ERR_NOT_ELIGIBLE,
    ERR_PARTIAL,
    LOG_PRUNE_CANDIDATES,
    LOG_PRUNE_DONE,
    LOG_PRUNE_REFUSED,
)
from rag_backend.domain.models.carousel import CarouselStatus
from rag_backend.infrastructure.database.checkpoint_prune_sql import (
    TableCounts,
    delete_prunable,
    prunable_counts,
    prunable_rows,
)
from rag_backend.infrastructure.database.models import CarouselProjectModel

logger = structlog.get_logger(__name__)

FINISHED_STATUSES = (CarouselStatus.COMPLETED.value, CarouselStatus.FAILED.value)
_BACKUP_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL
_BACKUP_MODE = 0o600
_BACKUP_LINE = '{{"table": "{table}", "row": {row}}}\n'
_autopilot_runs = table(
    AUTOPILOT_RUNS_TABLE, column("carousel_project_id"), column("state")
)


class PruneRefusedError(Exception):
    """The prune stopped before deleting anything (or rolled back)."""


@dataclass(frozen=True)
class PruneCandidate:
    """One eligible thread with its project's state and its prunable rows."""

    thread_id: str
    project_id: str
    status: str
    phase_status: str
    workflow_status: str
    is_public: bool
    archived: bool
    updated_at: datetime
    prunable: TableCounts


@dataclass(frozen=True)
class PruneRequest:
    """The signed-off threads, the eligibility cutoff and the backup file."""

    thread_ids: tuple[str, ...]
    cutoff: datetime
    backup_path: Path


ProjectRow = tuple[str, str, str | None, str, bool, datetime | None, datetime]


def _unsettled_autopilot_run() -> Select[tuple[int]]:
    runs = _autopilot_runs.c
    return select(literal(1)).where(
        runs.carousel_project_id == CarouselProjectModel.id,
        runs.state.not_in(AUTOPILOT_SETTLED_STATES),
    )


def _eligible_projects(cutoff: datetime) -> Select[ProjectRow]:
    model = CarouselProjectModel
    return select(
        model.id,
        model.status,
        model.phase_status,
        model.workflow_status,
        model.is_public,
        model.archived_at,
        model.updated_at,
    ).where(
        model.status.in_(FINISHED_STATUSES),
        model.updated_at < cutoff,
        model.needs_republish_since.is_(None),
        or_(
            model.phase_status.is_(None),
            model.phase_status != PHASE_STATUS_IN_PROGRESS,
        ),
        or_(model.phase_status == PHASE_STATUS_REJECTED, model.is_public.is_(True)),
        ~exists(_unsettled_autopilot_run()),
    )


def _candidate(project: ProjectRow, prunable: TableCounts) -> PruneCandidate:
    (
        project_id,
        status,
        phase_status,
        workflow_status,
        is_public,
        archived_at,
        updated,
    ) = project
    return PruneCandidate(
        thread_id=checkpoint_thread_id(project_id),
        project_id=project_id,
        status=status,
        phase_status=phase_status or "",
        workflow_status=workflow_status,
        is_public=is_public,
        archived=archived_at is not None,
        updated_at=updated,
        prunable=prunable,
    )


async def _candidates(
    conn: AsyncConnection, statement: Select[ProjectRow]
) -> list[PruneCandidate]:
    projects: dict[str, ProjectRow] = {
        checkpoint_thread_id(row[0]): row._tuple()
        for row in (await conn.execute(statement)).all()
    }
    counts = await prunable_counts(conn, list(projects))
    return [
        _candidate(projects[thread], prunable)
        for thread, prunable in sorted(counts.items())
        if prunable.total > 0
    ]


async def find_candidates(
    engine: AsyncEngine, cutoff: datetime
) -> list[PruneCandidate]:
    """The eligible threads that have prunable rows; deletes nothing."""
    async with engine.connect() as conn:
        found = await _candidates(conn, _eligible_projects(cutoff))
    logger.info(LOG_PRUNE_CANDIDATES, threads=len(found), cutoff=cutoff.isoformat())
    return found


def _write_backup(path: Path, rows: list[tuple[str, str]]) -> int:
    descriptor = os.open(path, _BACKUP_FLAGS, _BACKUP_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as backup:
        for table, row in rows:
            backup.write(_BACKUP_LINE.format(table=table, row=row))
        backup.flush()
        os.fsync(backup.fileno())
    with path.open(encoding="utf-8") as written:
        return sum(1 for _ in written)


def _refuse(message: str) -> PruneRefusedError:
    logger.error(LOG_PRUNE_REFUSED, reason=message)
    return PruneRefusedError(message)


async def _signed_off(conn: AsyncConnection, request: PruneRequest) -> list[str]:
    locked = _eligible_projects(request.cutoff).with_for_update()
    eligible = {c.thread_id for c in await _candidates(conn, locked)}
    stale = sorted(set(request.thread_ids) - eligible)
    if stale:
        raise _refuse(ERR_NOT_ELIGIBLE.format(threads=", ".join(stale)))
    return sorted(request.thread_ids)


async def apply_prune(engine: AsyncEngine, request: PruneRequest) -> TableCounts:
    """Back up and delete the prunable rows of the signed-off threads."""
    if not request.thread_ids:
        raise _refuse(ERR_NO_THREADS)
    async with engine.begin() as conn:
        threads = await _signed_off(conn, request)
        counts = await prunable_counts(conn, threads)
        expected = TableCounts()
        for prunable in counts.values():
            expected = expected.plus(prunable)
        written = _write_backup(request.backup_path, await prunable_rows(conn, threads))
        if written != expected.total:
            raise _refuse(
                ERR_BACKUP_MISMATCH.format(written=written, expected=expected.total)
            )
        deleted = await delete_prunable(conn, threads)
        if deleted.total == 0:
            raise _refuse(ERR_NOOP.format(expected=expected.total))
        if deleted != expected:
            raise _refuse(
                ERR_PARTIAL.format(deleted=deleted.total, expected=expected.total)
            )
    logger.info(
        LOG_PRUNE_DONE,
        threads=len(threads),
        checkpoints=deleted.checkpoints,
        writes=deleted.writes,
        blobs=deleted.blobs,
    )
    return deleted
