"""Which carousels may be archived, as SQL predicates and as one atomic UPDATE.

A carousel can be archived when it is not published, has no live run (a
``run_heartbeat_at`` newer than the stale window), and has no autopilot run that
is still going (any state other than published, rejected, expired or failed:
a scheduled run must still publish). A phase stuck ``in_progress`` with a stale
heartbeat can be archived. The automatic archive also skips carousels whose
status says the pipeline is generating.

Archiving is one conditional ``UPDATE ... WHERE <rules> RETURNING``, so a run or
a publish that starts between a read and the write is never archived. It sets
``archived_at`` only and keeps ``updated_at``, so archiving is not activity.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import (
    ColumnElement,
    and_,
    column,
    exists,
    not_,
    or_,
    select,
    table,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel import (
    CAROUSEL_STATUS_DESIGNING,
    CAROUSEL_STATUS_DRAFTING,
    CAROUSEL_STATUS_EXPORTING,
    CAROUSEL_STATUS_GENERATING_IMAGES,
    CAROUSEL_STATUS_RESEARCHING,
)
from rag_backend.domain.constants.carousel_archive import (
    ARCHIVE_REFUSED_AUTOPILOT,
    ARCHIVE_REFUSED_IN_PROGRESS,
    ARCHIVE_REFUSED_PUBLISHED,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_PUBLISHED
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

AUTOPILOT_FINISHED_STATES: tuple[str, ...] = (
    "published",
    "rejected",
    "expired",
    "failed",
)
"""Autopilot run states that no longer need the carousel."""

GENERATING_STATUSES: tuple[str, ...] = (
    CAROUSEL_STATUS_RESEARCHING,
    CAROUSEL_STATUS_DRAFTING,
    CAROUSEL_STATUS_DESIGNING,
    CAROUSEL_STATUS_GENERATING_IMAGES,
    CAROUSEL_STATUS_EXPORTING,
)
"""Carousel statuses of a pipeline that is (or claims to be) generating."""

_AUTOPILOT_RUNS = table(
    "autopilot_runs", column("carousel_project_id"), column("state")
)
_MODEL = CarouselProjectModel


def _active_autopilot_run() -> ColumnElement[bool]:
    """An autopilot run of the row's carousel that has not finished."""
    runs = _AUTOPILOT_RUNS.c
    return exists(
        select(runs.carousel_project_id).where(
            runs.carousel_project_id == _MODEL.id,
            runs.state.not_in(AUTOPILOT_FINISHED_STATES),
        )
    )


def _live_run(now: datetime, stale_seconds: int) -> ColumnElement[bool]:
    """The row's run heartbeat is newer than the stale window."""
    cutoff = now - timedelta(seconds=stale_seconds)
    return and_(_MODEL.run_heartbeat_at.is_not(None), _MODEL.run_heartbeat_at >= cutoff)


def _not_published() -> ColumnElement[bool]:
    return or_(_MODEL.current_phase.is_(None), _MODEL.current_phase != PHASE_PUBLISHED)


def archivable(now: datetime, stale_seconds: int) -> list[ColumnElement[bool]]:
    """Predicates of a carousel the owner may archive now (not archived yet)."""
    return [
        _MODEL.archived_at.is_(None),
        _not_published(),
        not_(_live_run(now, stale_seconds)),
        not_(_active_autopilot_run()),
    ]


def auto_archivable(
    now: datetime, stale_seconds: int, idle_cutoff: datetime
) -> list[ColumnElement[bool]]:
    """Predicates of a carousel the worker archives: archivable, idle, not running."""
    return [
        *archivable(now, stale_seconds),
        or_(_MODEL.status.is_(None), _MODEL.status.not_in(GENERATING_STATUSES)),
        _MODEL.updated_at <= idle_cutoff,
    ]


async def archive_where(
    db: AsyncSession, predicates: Sequence[ColumnElement[bool]], now: datetime
) -> list[str]:
    """Archive every carousel matching ``predicates`` in one UPDATE; their ids."""
    statement = (
        update(_MODEL)
        .where(*predicates)
        .values(archived_at=now, updated_at=_MODEL.updated_at)
        .returning(_MODEL.id)
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(statement)
    return [str(row[0]) for row in result.all()]


def heartbeat_stale_seconds() -> int:
    """Seconds after which a run heartbeat no longer counts as a live run."""
    return get_settings().workflow_run_heartbeat_stale_seconds


async def archive_refusal_of(
    db: AsyncSession, project_id: str, rule: tuple[datetime, int]
) -> str | None:
    """Why ``project_id`` cannot be archived now, read in one query, or ``None``."""
    now, stale_seconds = rule
    row = (
        await db.execute(
            select(
                _MODEL.current_phase,
                _live_run(now, stale_seconds),
                _active_autopilot_run(),
            ).where(_MODEL.id == project_id)
        )
    ).first()
    if row is None:
        return None
    phase, live, autopilot = row
    if phase == PHASE_PUBLISHED:
        return ARCHIVE_REFUSED_PUBLISHED
    if live:
        return ARCHIVE_REFUSED_IN_PROGRESS
    if autopilot:
        return ARCHIVE_REFUSED_AUTOPILOT
    return None


async def archive_refusals(
    db: AsyncSession, project_ids: Sequence[str], rule: tuple[datetime, int]
) -> dict[str, str]:
    """The refusal code of every listed carousel that cannot be archived now."""
    if not project_ids:
        return {}
    now, stale_seconds = rule
    rows = await db.execute(
        select(
            _MODEL.id,
            _MODEL.current_phase,
            _live_run(now, stale_seconds),
            _active_autopilot_run(),
        ).where(_MODEL.id.in_(list(project_ids)))
    )
    refusals: dict[str, str] = {}
    for project_id, phase, live, autopilot in rows.all():
        if phase == PHASE_PUBLISHED:
            refusals[str(project_id)] = ARCHIVE_REFUSED_PUBLISHED
        elif live:
            refusals[str(project_id)] = ARCHIVE_REFUSED_IN_PROGRESS
        elif autopilot:
            refusals[str(project_id)] = ARCHIVE_REFUSED_AUTOPILOT
    return refusals
