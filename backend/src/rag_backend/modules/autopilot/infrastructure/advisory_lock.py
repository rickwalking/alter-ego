"""Transaction-scoped Postgres advisory locks (QA r1/r2).

Topic intake and the scout-failed cap both read a count, then write. Two
concurrent requests would otherwise both pass the check before either
commits. The lock is released by the caller's commit or rollback. SQLite
(the unit-test database) has no advisory locks, so the call is a no-op there.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.recovery_constants import (
    ADVISORY_LOCK_PARAM,
    ADVISORY_LOCK_SQL,
    DIALECT_POSTGRESQL,
)


async def advisory_xact_lock(session: AsyncSession, key: int) -> None:
    """Block until this transaction holds advisory lock ``key``."""
    if session.get_bind().dialect.name != DIALECT_POSTGRESQL:
        return
    await session.execute(text(ADVISORY_LOCK_SQL), {ADVISORY_LOCK_PARAM: key})
