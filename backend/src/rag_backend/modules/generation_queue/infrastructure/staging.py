"""Stage a generation run in the caller's transaction (the outbox write).

Approvals call this inside their own transaction, next to their compare-and-set:
the row commits or rolls back with the approval, and PgQueuer is never touched,
so a missing or broken PgQueuer install can never undo an approval. A dedupe key
that is already active makes the insert a no-op (double tap, webhook retry).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import structlog
from sqlalchemy import CursorResult, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.generation_queue.constants import (
    LOG_STAGED,
    STATUS_QUEUED,
)
from rag_backend.modules.generation_queue.domain.models import StageCommand
from rag_backend.modules.generation_queue.infrastructure.models import (
    ACTIVE_WHERE_SQL,
    GenerationRunModel,
)

logger = structlog.get_logger()

_POSTGRESQL = "postgresql"
_DEDUPE_COLUMN = "dedupe_key"
_ACTIVE_WHERE = text(ACTIVE_WHERE_SQL)


def _values(command: StageCommand) -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "id": uuid4(),
        "kind": command.kind.value,
        "dedupe_key": command.dedupe_key,
        "status": STATUS_QUEUED,
        "payload": command.payload,
        "autopilot_run_id": command.autopilot_run_id,
        "carousel_project_id": command.carousel_project_id,
        "attempts": 0,
        "phase_attempts": {},
        "created_at": now,
        "updated_at": now,
    }


async def stage_generation_run(session: AsyncSession, command: StageCommand) -> bool:
    """Insert a queued run unless its dedupe key is active. The caller commits."""
    insert = (
        pg_insert if session.get_bind().dialect.name == _POSTGRESQL else sqlite_insert
    )
    statement = (
        insert(GenerationRunModel)
        .values(**_values(command))
        .on_conflict_do_nothing(
            index_elements=[_DEDUPE_COLUMN], index_where=_ACTIVE_WHERE
        )
    )
    result = await session.execute(statement)
    inserted = cast(CursorResult[object], result).rowcount == 1
    if inserted:
        logger.info(LOG_STAGED, kind=command.kind.value, dedupe_key=command.dedupe_key)
    return inserted


__all__ = ["stage_generation_run"]
