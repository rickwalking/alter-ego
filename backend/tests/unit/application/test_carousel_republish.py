"""Unit tests for the idempotent carousel republish service (AE-0313).

Feature: Republish a completed carousel's artifacts
  Scenario: Republish with unchanged content is a safe no-op
  Scenario: Concurrent republishes serialize on the build lock
  (see tests/features/carousel_republish.feature)

The advisory lock no-ops on SQLite (AE-0316), so the serialization semantics are
exercised here with an injected fake lock; the true-concurrency Postgres path is
covered by tests/integration/test_carousel_project_lock_pg.py.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from rag_backend.application.services.carousel.carousel_republish import (
    engine_from_session,
    republish_build_lock,
    republish_completed_carousel,
)
from rag_backend.application.services.carousel.editorial_finalize import (
    CarouselFinalizeResult,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_BUILD_IN_PROGRESS,
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
    CONFLICT_CODE_RUN_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)

_LOCK_TARGET = (
    "rag_backend.application.services.carousel.carousel_republish.carousel_project_lock"
)
_FINALIZE_TARGET = (
    "rag_backend.application.services.carousel.carousel_republish"
    ".finalize_carousel_after_images_approval"
)
PROJECT_ID = "66014ba3-2c50-48f2-b4b9-cbc241e07caf"


def _session_with_engine(engine: AsyncEngine) -> AsyncSession:
    return cast(AsyncSession, MagicMock(bind=engine))


class _SingleHolderLock:
    """Fake advisory lock that admits one holder; a second non-blocking
    acquire raises the AE-0316 ``mutation_in_progress`` conflict."""

    def __init__(self) -> None:
        self.held = False
        self.max_concurrent = 0
        self._active = 0

    @asynccontextmanager
    async def acquire(
        self,
        _engine: AsyncEngine,
        _project_id: str,
        *,
        blocking: bool = True,
    ) -> AsyncIterator[None]:
        if self.held and not blocking:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
            )
        self.held = True
        self._active += 1
        self.max_concurrent = max(self.max_concurrent, self._active)
        try:
            yield
        finally:
            self._active -= 1
            self.held = False


@pytest.mark.unit
class TestEngineFromSession:
    def test_returns_bound_async_engine(self) -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        db = _session_with_engine(engine)
        assert engine_from_session(db) is engine

    def test_raises_when_bind_is_not_async_engine(self) -> None:
        db = cast(AsyncSession, MagicMock(bind=MagicMock()))
        with pytest.raises(TypeError):
            engine_from_session(db)


@pytest.mark.asyncio
@pytest.mark.unit
class TestRepublishBuildLock:
    async def test_translates_mutation_to_build_in_progress(self) -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        @asynccontextmanager
        async def _raising(*_args: object, **_kwargs: object) -> AsyncIterator[None]:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
            )
            yield

        with patch(_LOCK_TARGET, _raising), pytest.raises(CarouselConflictError) as exc:
            async with republish_build_lock(engine, PROJECT_ID):
                pass
        assert exc.value.conflict.code == CONFLICT_CODE_BUILD_IN_PROGRESS

    async def test_passes_through_unrelated_conflict(self) -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        @asynccontextmanager
        async def _raising(*_args: object, **_kwargs: object) -> AsyncIterator[None]:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
            )
            yield

        with patch(_LOCK_TARGET, _raising), pytest.raises(CarouselConflictError) as exc:
            async with republish_build_lock(engine, PROJECT_ID):
                pass
        assert exc.value.conflict.code == CONFLICT_CODE_RUN_IN_PROGRESS


@pytest.mark.asyncio
@pytest.mark.unit
class TestRepublishCompletedCarousel:
    async def test_runs_finalize_under_the_lock(self) -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        db = _session_with_engine(engine)
        finalize = AsyncMock(
            return_value=CarouselFinalizeResult(completed=True, errors=())
        )
        lock = _SingleHolderLock()
        with (
            patch(_LOCK_TARGET, lock.acquire),
            patch(_FINALIZE_TARGET, finalize),
        ):
            result = await republish_completed_carousel(db, PROJECT_ID)
        assert result.completed
        finalize.assert_awaited_once_with(db, PROJECT_ID)

    async def test_concurrent_republishes_serialize_on_the_lock(self) -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        db = _session_with_engine(engine)
        lock = _SingleHolderLock()
        release = asyncio.Event()

        async def _hold(_db: object, _project_id: str) -> CarouselFinalizeResult:
            await release.wait()
            return CarouselFinalizeResult(completed=True, errors=())

        with (
            patch(_LOCK_TARGET, lock.acquire),
            patch(_FINALIZE_TARGET, AsyncMock(side_effect=_hold)),
        ):
            first = asyncio.create_task(republish_completed_carousel(db, PROJECT_ID))
            await asyncio.sleep(0)  # let the first task acquire the lock
            second = asyncio.create_task(republish_completed_carousel(db, PROJECT_ID))
            conflict: CarouselConflictError | None = None
            try:
                await second
            except CarouselConflictError as exc:
                conflict = exc
            release.set()
            await first

        # Exactly one holder was ever inside the critical section.
        assert lock.max_concurrent == 1
        assert conflict is not None
        assert conflict.conflict.code == CONFLICT_CODE_BUILD_IN_PROGRESS
