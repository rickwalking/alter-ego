"""Transaction-scoped Postgres lock timeout for run-column writers (AE-0320).

The background resume runner holds its main session's transaction (flushed row
updates + notification inserts) while stage-boundary heartbeats and the stale
run reaper write the same ``carousel_projects`` row from SEPARATE sessions.
Without a lock timeout those writers queue indefinitely behind the runner's own
uncommitted transaction — and because the runner AWAITS the stage heartbeat
inline, the queueing is a self-deadlock (observed on prod 2026-07-18: five out
of five gate approvals wedged until manual ``pg_terminate_backend``).

``SET LOCAL lock_timeout`` bounds every such write to a fail-fast error the
caller treats as a soft failure (heartbeat: retry/skip; reaper: next tick).
SQLite (unit tests) has no lock_timeout and its file lock never exhibits the
cross-session row-lock wait — dialect-gated no-op, mirroring the AE-0316
advisory-lock pattern.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_run import RUN_WRITE_LOCK_TIMEOUT_MS

_POSTGRESQL_DIALECT = "postgresql"

# Static statement assembled once from a trusted module constant (an int) —
# no request data ever reaches this string.
_SET_LOCK_TIMEOUT_SQL = text(
    "SET LOCAL lock_timeout = '" + str(int(RUN_WRITE_LOCK_TIMEOUT_MS)) + "ms'"
)


async def apply_run_write_lock_timeout(session: AsyncSession) -> None:
    """Bound row-lock waits for the current transaction (Postgres only)."""
    bind = session.get_bind()
    if bind.dialect.name != _POSTGRESQL_DIALECT:
        return
    await session.execute(_SET_LOCK_TIMEOUT_SQL)


__all__ = ["apply_run_write_lock_timeout"]
