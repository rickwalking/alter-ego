"""The safety files of the checkpoint prune: JSONL backup, restore, pg_dump check.

Every row the prune deletes is written first, one JSON object per line
(``{"table": ..., "row": ...}``) to a new owner-only file. ``restore_backup``
inserts those rows back with ``jsonb_populate_record``, so the backup is a real
restore path, not just a count. ``verify_pg_dump`` asks ``pg_restore --list``
whether a ``pg_dump -Fc`` archive is readable and holds the data of the three
checkpoint tables before anything is deleted.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path

import structlog
from sqlalchemy import (
    Insert,
    bindparam,
    column,
    func,
    inspect,
    literal_column,
    select,
    table,
)
from sqlalchemy import insert as sql_insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.domain.constants.checkpoint_prune import (
    BACKUP_ROW_KEY,
    BACKUP_TABLE_KEY,
    CHECKPOINT_BLOBS_TABLE,
    CHECKPOINT_WRITES_TABLE,
    CHECKPOINTS_TABLE,
    ERR_BACKUP_LINE,
    ERR_PG_DUMP_TABLES,
    ERR_PG_DUMP_UNREADABLE,
    ERR_PG_RESTORE_MISSING,
    LOG_PRUNE_REFUSED,
    LOG_PRUNE_RESTORED,
    PG_DUMP_TABLE_DATA,
    PG_RESTORE_BINARY,
    PG_RESTORE_LIST_FLAG,
    PG_RESTORE_TIMEOUT_SECONDS,
)
from rag_backend.infrastructure.database.checkpoint_prune_sql import TableCounts

logger = structlog.get_logger(__name__)

CHECKPOINT_TABLES = (CHECKPOINTS_TABLE, CHECKPOINT_WRITES_TABLE, CHECKPOINT_BLOBS_TABLE)
_BACKUP_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL
_BACKUP_MODE = 0o600
_ROW_PARAM = "row"
_RECORD_ALIAS = "restored"


class PruneRefusedError(Exception):
    """The prune stopped before deleting anything (or rolled back)."""


def refuse(message: str) -> PruneRefusedError:
    """Log the refusal and build the error to raise."""
    logger.error(LOG_PRUNE_REFUSED, reason=message)
    return PruneRefusedError(message)


def write_backup(path: Path, rows: list[tuple[str, str]]) -> int:
    """Write the rows to a new owner-only file; return the lines on disk."""
    descriptor = os.open(path, _BACKUP_FLAGS, _BACKUP_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as backup:
        for name, row in rows:
            entry = {BACKUP_TABLE_KEY: name, BACKUP_ROW_KEY: json.loads(row)}
            backup.write(json.dumps(entry, sort_keys=True) + "\n")
        backup.flush()
        os.fsync(backup.fileno())
    with path.open(encoding="utf-8") as written:
        return sum(1 for _ in written)


def _read_backup(path: Path) -> dict[str, list[dict[str, object]]]:
    by_table: dict[str, list[dict[str, object]]] = {
        name: [] for name in CHECKPOINT_TABLES
    }
    with path.open(encoding="utf-8") as backup:
        for number, line in enumerate(backup, start=1):
            entry = json.loads(line)
            rows = by_table.get(str(entry.get(BACKUP_TABLE_KEY)))
            row = entry.get(BACKUP_ROW_KEY)
            if rows is None or not isinstance(row, dict):
                raise refuse(ERR_BACKUP_LINE.format(line=number))
            rows.append({_ROW_PARAM: row})
    return by_table


def _columns(sync: Connection, name: str) -> list[str]:
    return [str(col["name"]) for col in inspect(sync).get_columns(name)]


def _restore_statement(name: str, columns: list[str]) -> Insert:
    record = (
        func
        .jsonb_populate_record(
            literal_column(f"NULL::{name}"), bindparam(_ROW_PARAM, type_=JSONB)
        )
        .table_valued(*columns)
        .alias(_RECORD_ALIAS)
    )
    target = table(name, *(column(col) for col in columns))
    return sql_insert(target).from_select(
        columns, select(*(record.c[col] for col in columns))
    )


async def restore_backup(engine: AsyncEngine, path: Path) -> TableCounts:
    """Insert every backed-up row again, all or nothing."""
    by_table = _read_backup(path)
    restored: dict[str, int] = {}
    async with engine.begin() as conn:
        for name, rows in by_table.items():
            restored[name] = len(rows)
            if not rows:
                continue
            columns = await conn.run_sync(_columns, name)
            await conn.execute(_restore_statement(name, columns), rows)
    counts = TableCounts(
        checkpoints=restored[CHECKPOINTS_TABLE],
        writes=restored[CHECKPOINT_WRITES_TABLE],
        blobs=restored[CHECKPOINT_BLOBS_TABLE],
    )
    logger.info(LOG_PRUNE_RESTORED, rows=counts.total, backup=str(path))
    return counts


def _tables_with_data(listing: str) -> set[str]:
    found: set[str] = set()
    marker = list(PG_DUMP_TABLE_DATA)
    for line in listing.splitlines():
        tokens = line.split()
        for index in range(len(tokens) - len(marker) - 1):
            if tokens[index : index + len(marker)] == marker:
                found.add(tokens[index + len(marker) + 1])
    return found


async def verify_pg_dump(path: Path) -> None:
    """Refuse unless ``pg_restore --list`` reads the archive and its table data."""
    binary = shutil.which(PG_RESTORE_BINARY)
    if binary is None:
        raise refuse(ERR_PG_RESTORE_MISSING)
    process = await asyncio.create_subprocess_exec(
        binary,
        PG_RESTORE_LIST_FLAG,
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await asyncio.wait_for(
        process.communicate(), timeout=PG_RESTORE_TIMEOUT_SECONDS
    )
    if process.returncode != 0:
        detail = err.decode(errors="replace").strip()
        raise refuse(ERR_PG_DUMP_UNREADABLE.format(detail=detail))
    missing = sorted(set(CHECKPOINT_TABLES) - _tables_with_data(out.decode()))
    if missing:
        raise refuse(ERR_PG_DUMP_TABLES.format(tables=", ".join(missing)))
