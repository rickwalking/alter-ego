"""Unit tests for the server-guaranteed republish sweeper (AE-0314).

Gherkin: tests/features/carousel_text_edit_no_regen.feature

The sweep republishes any completed carousel whose ``needs_republish_since``
marker is older than the configured window and clears the marker on success —
the guarantee behind a client that never called republish. The heavy finalize
pipeline is stubbed; the sweep's selection + marker lifecycle is the unit.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel import carousel_republish
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_BUILD_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.infrastructure.database.carousel_republish_sweeper import (
    CarouselRepublishSweeperConfig,
    CarouselRepublishSweeperRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_rows(test_engine: AsyncEngine) -> AsyncIterator[None]:
    yield
    async with _factory(test_engine)() as db:
        await db.execute(delete(CarouselProjectModel))
        await db.commit()


async def _add_project(
    db: AsyncSession,
    *,
    marker_age_seconds: int | None,
    status: str = "completed",
) -> str:
    marker = (
        None
        if marker_age_seconds is None
        else datetime.now(UTC) - timedelta(seconds=marker_age_seconds)
    )
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Sweep",
        audience="Devs",
        niche="Tech",
        status=status,
        needs_republish_since=marker,
    )
    db.add(project)
    await db.commit()
    return str(project.id)


def _sweeper(min_age: int = 60) -> CarouselRepublishSweeperRepository:
    return CarouselRepublishSweeperRepository(
        CarouselRepublishSweeperConfig(min_age_seconds=min_age)
    )


async def _marker(db: AsyncSession, project_id: str) -> datetime | None:
    return await db.scalar(
        select(CarouselProjectModel.needs_republish_since).where(
            CarouselProjectModel.id == project_id
        )
    )


@pytest.mark.asyncio
class TestRepublishSweeper:
    async def test_overdue_marker_is_republished_and_cleared(
        self, test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []

        async def _fake_republish(_db: AsyncSession, project_id: str) -> object:
            calls.append(project_id)
            return SimpleNamespace(completed=True, errors=())

        monkeypatch.setattr(
            carousel_republish, "republish_completed_carousel", _fake_republish
        )
        async with _factory(test_engine)() as db:
            pid = await _add_project(db, marker_age_seconds=600)
            count = await _sweeper().sweep(db)
            assert count == 1
            assert calls == [pid]
            assert await _marker(db, pid) is None

    async def test_fresh_marker_is_not_swept(
        self, test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _fake_republish(_db: AsyncSession, _pid: str) -> object:
            raise AssertionError("fresh marker must not be republished")

        monkeypatch.setattr(
            carousel_republish, "republish_completed_carousel", _fake_republish
        )
        async with _factory(test_engine)() as db:
            pid = await _add_project(db, marker_age_seconds=5)
            count = await _sweeper(min_age=180).sweep(db)
            assert count == 0
            assert await _marker(db, pid) is not None

    async def test_build_conflict_is_swallowed_and_marker_kept(
        self, test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _fake_republish(_db: AsyncSession, _pid: str) -> object:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_BUILD_IN_PROGRESS)
            )

        monkeypatch.setattr(
            carousel_republish, "republish_completed_carousel", _fake_republish
        )
        async with _factory(test_engine)() as db:
            pid = await _add_project(db, marker_age_seconds=600)
            count = await _sweeper().sweep(db)
            assert count == 0
            # A concurrent client republish holds the lock; retry next tick.
            assert await _marker(db, pid) is not None
