"""ORM-level run-progress invariants + epoch fence for carousels (AE-0315).

Two enforcement mechanisms live here, both registered once at import time
(via ``infrastructure.database.models``):

1. **Atomic run-column invariant** — a ``before_update`` listener on
   :class:`CarouselProjectModel`: whenever ``phase_status`` *changes value*
   (never on no-op hydrates) the run columns are kept consistent inside the
   SAME flush UPDATE — transition INTO ``in_progress`` stamps
   ``run_started_at``/``run_heartbeat_at``; transition to any non-in_progress
   value clears them. This covers the three write-owner bypass sites
   (``workflow_timeout_repository._reject``, the phase-5 migration backfill,
   and the ``update_from_entity`` hydrator) without per-site edits, and a
   crash can never leave a terminal row with a live-looking run.

2. **Flush-boundary epoch fence (layer a)** — a ``before_flush`` listener on
   the sync :class:`Session` class rejecting mutations to
   ``CarouselProjectModel``/``CarouselSlideModel`` rows when the current
   execution context is run-owned (``carousel_run_epoch`` contextvar set) AND
   its captured epoch mismatches the row's *current* ``run_epoch`` read
   inside the flush transaction. Contextvar unset → pass-through: user/API/
   admin/operator writes are never epoch-stamped and can never be falsely
   rejected by a concurrent reap (pinned cold-critic r6). Correctness holds
   at READ COMMITTED because the comparison reads the row's current value in
   the flush transaction.

The module also registers the async run-epoch reader used by the workflow
engine's checkpoint-commit boundary (layer b) through the domain DI seam.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import event, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.domain.models.carousel_run import (
    StaleRunEpochError,
    current_run_context,
    register_run_epoch_reader,
)
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.orm import Mapper, UOWTransaction

_PHASE_STATUS_ATTR = "phase_status"


def _sync_run_columns_on_phase_transition(
    _mapper: Mapper[CarouselProjectModel],
    _connection: Connection,
    target: CarouselProjectModel,
) -> None:
    """Stamp/clear run columns atomically with a phase_status value change."""
    history = get_history(target, _PHASE_STATUS_ATTR)
    if not history.has_changes():
        return
    new_value = history.added[0] if history.added else target.phase_status
    old_value = history.deleted[0] if history.deleted else None
    if old_value == new_value:
        # No-op hydrate (e.g. update_from_entity re-writing the same value):
        # never spuriously clear a live run's columns.
        return
    if new_value == PHASE_STATUS_IN_PROGRESS:
        now = datetime.now(UTC)
        target.run_started_at = now
        target.run_heartbeat_at = now
        return
    target.run_started_at = None
    target.run_heartbeat_at = None


def _guarded_project_id(instance: object) -> str | None:
    """Project id for a guarded instance, or None when not guarded."""
    if isinstance(instance, CarouselProjectModel):
        return str(instance.id)
    if isinstance(instance, CarouselSlideModel):
        return str(instance.project_id)
    return None


def _current_epoch_of(session: Session, project_id: str) -> int | None:
    """Read the row's current run_epoch inside the flush transaction."""
    with session.no_autoflush:
        return session.execute(
            select(CarouselProjectModel.run_epoch).where(
                CarouselProjectModel.id == project_id
            )
        ).scalar_one_or_none()


def _enforce_run_epoch_fence(
    session: Session,
    _flush_context: UOWTransaction,
    _instances: object | None,
) -> None:
    """Reject run-owned mutations whose captured epoch is stale (layer a)."""
    ctx = current_run_context()
    if ctx is None:
        return
    for instance in [*session.new, *session.dirty, *session.deleted]:
        project_id = _guarded_project_id(instance)
        if project_id is None or project_id != ctx.project_id:
            continue
        if instance in session.dirty and not session.is_modified(instance):
            continue
        current = _current_epoch_of(session, project_id)
        if current is not None and current != ctx.epoch:
            raise StaleRunEpochError(project_id)
        return


async def _read_current_run_epoch(project_id: str) -> int | None:
    """Async run-epoch reader for the engine checkpoint boundary (layer b)."""
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        result = await session.execute(
            select(CarouselProjectModel.run_epoch).where(
                CarouselProjectModel.id == project_id
            )
        )
        return result.scalar_one_or_none()


class _GuardRegistry:
    """Idempotent one-shot registration flag."""

    registered: bool = False


def register_carousel_run_guards() -> None:
    """Attach the run-column invariant + epoch fence listeners (idempotent)."""
    if _GuardRegistry.registered:
        return
    _GuardRegistry.registered = True
    event.listen(
        CarouselProjectModel,
        "before_update",
        _sync_run_columns_on_phase_transition,
    )
    event.listen(Session, "before_flush", _enforce_run_epoch_fence)
    register_run_epoch_reader(_read_current_run_epoch)


# Self-register on import: the models package re-exports this module, so the
# listeners are attached as soon as the ORM models are importable.
register_carousel_run_guards()

__all__ = ["register_carousel_run_guards"]
