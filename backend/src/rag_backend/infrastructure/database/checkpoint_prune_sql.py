"""Keep-latest queries over the LangGraph Postgres checkpoint tables.

For each (thread, namespace) the latest checkpoint is the highest
``checkpoint_id`` (the saver reads it the same way). It stays, together with the
writes of that checkpoint and of its parent (the saver reads the parent's pending
sends) and the blobs its ``channel_versions`` point at. Every other row of the
thread is prunable. Queries are SQLAlchemy Core; thread ids are bound parameters.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import (
    ColumnElement,
    Subquery,
    TableClause,
    and_,
    column,
    delete,
    exists,
    func,
    literal,
    not_,
    select,
    table,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncConnection

from rag_backend.domain.constants.checkpoint_prune import (
    CHANNEL_VERSIONS_KEY,
    CHECKPOINT_BLOBS_TABLE,
    CHECKPOINT_WRITES_TABLE,
    CHECKPOINTS_TABLE,
)

_THREAD = "thread_id"
_NAMESPACE = "checkpoint_ns"
_CHECKPOINT_ID = "checkpoint_id"
_PARENT_ID = "parent_checkpoint_id"
_CHECKPOINT = "checkpoint"

checkpoints = table(
    CHECKPOINTS_TABLE,
    column(_THREAD),
    column(_NAMESPACE),
    column(_CHECKPOINT_ID),
    column(_PARENT_ID),
    column(_CHECKPOINT, JSONB),
)
checkpoint_writes = table(
    CHECKPOINT_WRITES_TABLE, column(_THREAD), column(_NAMESPACE), column(_CHECKPOINT_ID)
)
checkpoint_blobs = table(
    CHECKPOINT_BLOBS_TABLE,
    column(_THREAD),
    column(_NAMESPACE),
    column("channel"),
    column("version"),
)


@dataclass(frozen=True)
class TableCounts:
    """Row counts per checkpoint table."""

    checkpoints: int = 0
    writes: int = 0
    blobs: int = 0

    @property
    def total(self) -> int:
        """All rows together."""
        return self.checkpoints + self.writes + self.blobs

    def plus(self, other: TableCounts) -> TableCounts:
        """The table-wise sum of two counts."""
        return TableCounts(
            checkpoints=self.checkpoints + other.checkpoints,
            writes=self.writes + other.writes,
            blobs=self.blobs + other.blobs,
        )


def _latest(thread_ids: list[str]) -> Subquery:
    c = checkpoints.c
    return (
        select(
            c.thread_id,
            c.checkpoint_ns,
            c.checkpoint_id,
            c.parent_checkpoint_id,
            c.checkpoint,
        )
        .where(c.thread_id.in_(thread_ids))
        .distinct(c.thread_id, c.checkpoint_ns)
        .order_by(c.thread_id, c.checkpoint_ns, c.checkpoint_id.desc())
        .subquery("latest")
    )


def _same_namespace(latest: Subquery, rows: TableClause) -> ColumnElement[bool]:
    return and_(
        latest.c.thread_id == rows.c.thread_id,
        latest.c.checkpoint_ns == rows.c.checkpoint_ns,
    )


def _old_checkpoint(thread_ids: list[str]) -> ColumnElement[bool]:
    latest = _latest(thread_ids)
    newer = select(literal(1)).where(
        _same_namespace(latest, checkpoints),
        latest.c.checkpoint_id != checkpoints.c.checkpoint_id,
    )
    return and_(checkpoints.c.thread_id.in_(thread_ids), exists(newer))


def _old_write(thread_ids: list[str]) -> ColumnElement[bool]:
    latest = _latest(thread_ids)
    kept_ids = (
        latest.c.checkpoint_id,
        func.coalesce(latest.c.parent_checkpoint_id, latest.c.checkpoint_id),
    )
    kept = select(literal(1)).where(
        _same_namespace(latest, checkpoint_writes),
        checkpoint_writes.c.checkpoint_id.in_(kept_ids),
    )
    return and_(checkpoint_writes.c.thread_id.in_(thread_ids), not_(exists(kept)))


def _old_blob(thread_ids: list[str]) -> ColumnElement[bool]:
    latest = _latest(thread_ids)
    versions = (
        func
        .jsonb_each_text(latest.c.checkpoint[CHANNEL_VERSIONS_KEY])
        .table_valued("key", "value")
        .lateral("v")
    )
    kept = (
        select(literal(1))
        .select_from(latest.join(versions, true()))
        .where(
            _same_namespace(latest, checkpoint_blobs),
            versions.c.key == checkpoint_blobs.c.channel,
            versions.c.value == checkpoint_blobs.c.version,
        )
    )
    return and_(checkpoint_blobs.c.thread_id.in_(thread_ids), not_(exists(kept)))


Predicate = Callable[[list[str]], ColumnElement[bool]]
DELETE_ORDER: tuple[tuple[TableClause, Predicate], ...] = (
    (checkpoint_writes, _old_write),
    (checkpoint_blobs, _old_blob),
    (checkpoints, _old_checkpoint),
)


def _counts(by_table: dict[str, int]) -> TableCounts:
    return TableCounts(
        checkpoints=by_table.get(CHECKPOINTS_TABLE, 0),
        writes=by_table.get(CHECKPOINT_WRITES_TABLE, 0),
        blobs=by_table.get(CHECKPOINT_BLOBS_TABLE, 0),
    )


async def prunable_counts(
    conn: AsyncConnection, thread_ids: list[str]
) -> dict[str, TableCounts]:
    """Prunable rows per thread (threads with none are left out)."""
    per_thread: dict[str, dict[str, int]] = {}
    for rows, prunable in DELETE_ORDER:
        statement = (
            select(rows.c.thread_id, func.count())
            .where(prunable(thread_ids))
            .group_by(rows.c.thread_id)
        )
        for thread_id, count in (await conn.execute(statement)).all():
            per_thread.setdefault(str(thread_id), {})[rows.name] = int(count)
    return {thread: _counts(tables) for thread, tables in per_thread.items()}


async def prunable_rows(
    conn: AsyncConnection, thread_ids: list[str]
) -> list[tuple[str, str]]:
    """Every prunable row as ``(table, row JSON)``, in delete order."""
    found: list[tuple[str, str]] = []
    for rows, prunable in DELETE_ORDER:
        as_json = func.to_jsonb(rows.table_valued())
        result = await conn.execute(select(as_json).where(prunable(thread_ids)))
        found.extend(
            (rows.name, json.dumps(row, sort_keys=True)) for (row,) in result.all()
        )
    return found


async def delete_prunable(conn: AsyncConnection, thread_ids: list[str]) -> TableCounts:
    """Delete the prunable rows (writes, blobs, then checkpoints)."""
    deleted: dict[str, int] = {}
    for rows, prunable in DELETE_ORDER:
        result = await conn.execute(delete(rows).where(prunable(thread_ids)))
        deleted[rows.name] = int(result.rowcount or 0)
    return _counts(deleted)
