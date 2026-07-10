"""Postgres integration tests for the carousel serialization lock (AE-0316).

Requires a Postgres ``DATABASE_URL`` (the CI ``postgres`` service or a local
instance); skipped otherwise, matching test_schema_drift_live.py.

Gherkin: tests/features/carousel_typed_conflicts.feature
"""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.modules.editorial.public import (
    carousel_project_lock,
    is_carousel_project_lock_held,
)

_async_url = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not _async_url or "postgresql" not in _async_url,
    reason="advisory-lock integration tests need a Postgres DATABASE_URL",
)

PROJECT_ID = "66014ba3-2c50-48f2-b4b9-cbc241e07caf"
HOLD_RELEASE_TIMEOUT_S = 5.0


class TestAdvisoryLockSemantics:
    """Scenario: advisory lock serializes concurrent holders."""

    async def test_try_acquire_conflicts_while_held(self) -> None:
        engine = create_async_engine(str(_async_url))
        try:
            async with carousel_project_lock(engine, PROJECT_ID):
                assert await is_carousel_project_lock_held(engine, PROJECT_ID)
                with pytest.raises(CarouselConflictError) as exc_info:
                    async with carousel_project_lock(
                        engine, PROJECT_ID, blocking=False
                    ):
                        pass
                assert (
                    exc_info.value.conflict.code
                    == CONFLICT_CODE_MUTATION_IN_PROGRESS
                )
            assert not await is_carousel_project_lock_held(engine, PROJECT_ID)
        finally:
            await engine.dispose()

    async def test_blocking_holder_waits_for_release(self) -> None:
        engine = create_async_engine(str(_async_url))
        entered = asyncio.Event()
        release = asyncio.Event()
        order: list[str] = []

        async def first_holder() -> None:
            async with carousel_project_lock(engine, PROJECT_ID):
                order.append("first-acquired")
                entered.set()
                await release.wait()
            order.append("first-released")

        async def second_holder() -> None:
            await entered.wait()
            async with carousel_project_lock(engine, PROJECT_ID):
                order.append("second-acquired")

        try:
            first = asyncio.create_task(first_holder())
            second = asyncio.create_task(second_holder())
            await asyncio.wait_for(entered.wait(), HOLD_RELEASE_TIMEOUT_S)
            release.set()
            await asyncio.wait_for(
                asyncio.gather(first, second), HOLD_RELEASE_TIMEOUT_S
            )
            assert order == ["first-acquired", "first-released", "second-acquired"]
        finally:
            await engine.dispose()

    async def test_lock_spans_sequential_transactions(self) -> None:
        """Session-scoped semantics: the lock survives commits by the holder."""
        engine = create_async_engine(str(_async_url))
        try:
            async with carousel_project_lock(engine, PROJECT_ID):
                async with engine.begin() as txn_one:
                    await txn_one.execute(text("SELECT 1"))
                async with engine.begin() as txn_two:
                    await txn_two.execute(text("SELECT 1"))
                assert await is_carousel_project_lock_held(engine, PROJECT_ID)
        finally:
            await engine.dispose()
