"""Unit tests for the per-project carousel serialization lock (AE-0316).

Postgres-specific semantics (real advisory locks, session scope,
concurrency) live in tests/integration/test_carousel_project_lock_pg.py;
these unit tests cover the key derivation and the dialect gating that keeps
the SQLite test fixtures working.

Gherkin: tests/features/carousel_typed_conflicts.feature
"""

from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.modules.editorial.public import (
    carousel_project_lock,
    carousel_project_lock_key,
    is_carousel_project_lock_held,
)

PROJECT_ID = "66014ba3-2c50-48f2-b4b9-cbc241e07caf"
OTHER_PROJECT_ID = "38affb3e-c219-4c56-9838-9cae7094f767"
SIGNED_64_MIN = -(2**63)
SIGNED_64_MAX = 2**63 - 1


class TestCarouselProjectLockKey:
    """Scenario: lock keys are stable, distinct, and Postgres-compatible."""

    def test_key_is_deterministic(self) -> None:
        assert carousel_project_lock_key(PROJECT_ID) == carousel_project_lock_key(
            PROJECT_ID
        )

    def test_keys_differ_per_project(self) -> None:
        assert carousel_project_lock_key(PROJECT_ID) != carousel_project_lock_key(
            OTHER_PROJECT_ID
        )

    def test_key_fits_signed_bigint(self) -> None:
        key = carousel_project_lock_key(PROJECT_ID)
        assert SIGNED_64_MIN <= key <= SIGNED_64_MAX


class TestDialectGating:
    """Scenario: non-Postgres engines no-op instead of querying pg catalogs."""

    async def test_lock_context_noops_on_sqlite(self) -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with carousel_project_lock(engine, PROJECT_ID):
                pass  # must not touch pg_advisory_lock on SQLite
        finally:
            await engine.dispose()

    async def test_held_check_reports_false_on_sqlite(self) -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            assert not await is_carousel_project_lock_held(engine, PROJECT_ID)
        finally:
            await engine.dispose()
