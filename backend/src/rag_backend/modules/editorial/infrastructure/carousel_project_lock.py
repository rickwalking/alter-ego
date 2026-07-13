"""Per-project carousel serialization lock (AE-0316).

Session-scoped Postgres advisory lock (``pg_advisory_lock`` /
``pg_advisory_unlock``) held on a dedicated connection so it spans multiple
sequential transactions — required by AE-0311's two-commit repair contract
(a transaction-scoped lock would release at the first commit).

Serialization-domain contract
-----------------------------
The lock serializes the **artifact-affecting mutators**: AE-0311 repair,
AE-0313 republish, and AE-0314's completed-project slide update. The
background resume runner and AE-0315's reaper deliberately do NOT acquire
it — resume-vs-mutator safety comes from the resume-start guard
(``is_carousel_project_lock_held`` → typed ``mutation_in_progress`` 409)
plus the ``lock_version`` CAS, and reap-vs-mutator safety from the reaper's
``lock_version``/``run_epoch`` bump (AE-0315).

The lock key is a stable signed 64-bit digest of the project UUID. Unlock is
guaranteed by the context manager ``finally`` on the same connection; a
dropped connection releases the lock server-side, and because the connection
is closed (not returned dirty to the pool) a crashed request can never leak
a held lock into an unrelated request.
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)

_ADVISORY_LOCK_SQL = text("SELECT pg_advisory_lock(:key)")
_ADVISORY_TRY_LOCK_SQL = text("SELECT pg_try_advisory_lock(:key)")
_ADVISORY_UNLOCK_SQL = text("SELECT pg_advisory_unlock(:key)")
_ADVISORY_HELD_SQL = text(
    "SELECT EXISTS ("
    "SELECT 1 FROM pg_locks "
    "WHERE locktype = 'advisory' AND granted "
    "AND classid = :classid AND objid = :objid AND objsubid = 1"
    ")"
)

_UUID_DIGEST_BYTES = 8
_POSTGRESQL_DIALECT = "postgresql"


def _is_postgres(bind_dialect_name: str) -> bool:
    """Advisory locks exist only on Postgres; other dialects no-op.

    Non-Postgres engines appear only in tests (SQLite in-memory). The lock's
    real semantics are covered by Postgres-marked integration tests; under
    SQLite the mutators run unserialized, which is safe for single-threaded
    unit tests and keeps the fixtures dialect-agnostic.
    """
    return bind_dialect_name == _POSTGRESQL_DIALECT


def carousel_project_lock_key(project_id: str) -> int:
    """Stable signed 64-bit advisory-lock key for a project id."""
    digest = hashlib.sha256(project_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:_UUID_DIGEST_BYTES], "big", signed=True)


def _key_halves(key: int) -> tuple[int, int]:
    """Split a signed 64-bit key into pg_locks classid/objid (uint32 halves)."""
    unsigned = key & 0xFFFFFFFFFFFFFFFF
    return (unsigned >> 32) & 0xFFFFFFFF, unsigned & 0xFFFFFFFF


def _mutation_in_progress_error() -> CarouselConflictError:
    return CarouselConflictError(
        CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
    )


@asynccontextmanager
async def carousel_project_lock(
    engine: AsyncEngine,
    project_id: str,
    *,
    blocking: bool = True,
) -> AsyncIterator[None]:
    """Hold the per-project advisory lock for the duration of the context.

    ``blocking=False`` uses ``pg_try_advisory_lock`` and raises the typed
    ``mutation_in_progress`` conflict when another holder has the lock.
    """
    if not _is_postgres(engine.dialect.name):
        yield
        return
    key = carousel_project_lock_key(project_id)
    connection = await engine.connect()
    try:
        if blocking:
            await connection.execute(_ADVISORY_LOCK_SQL, {"key": key})
        else:
            acquired = await connection.scalar(_ADVISORY_TRY_LOCK_SQL, {"key": key})
            if not acquired:
                raise _mutation_in_progress_error()
        try:
            yield
        finally:
            await connection.execute(_ADVISORY_UNLOCK_SQL, {"key": key})
    finally:
        await connection.close()


async def is_carousel_project_lock_held(
    engine: AsyncEngine,
    project_id: str,
) -> bool:
    """Return True when any session currently holds the project's lock."""
    if not _is_postgres(engine.dialect.name):
        return False
    classid, objid = _key_halves(carousel_project_lock_key(project_id))
    async with engine.connect() as connection:
        held = await connection.scalar(
            _ADVISORY_HELD_SQL, {"classid": classid, "objid": objid}
        )
    return bool(held)


async def is_carousel_project_lock_held_session(
    db: AsyncSession,
    project_id: str,
) -> bool:
    """Session-based variant of the lock-held check (for request scopes)."""
    bind = db.get_bind()
    if not _is_postgres(bind.dialect.name):
        return False
    classid, objid = _key_halves(carousel_project_lock_key(project_id))
    held = await db.scalar(_ADVISORY_HELD_SQL, {"classid": classid, "objid": objid})
    return bool(held)


__all__ = [
    "carousel_project_lock",
    "carousel_project_lock_key",
    "is_carousel_project_lock_held",
    "is_carousel_project_lock_held_session",
]
