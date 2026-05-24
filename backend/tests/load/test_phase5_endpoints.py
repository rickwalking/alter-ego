"""Load tests for Phase 5 migration (DEPLOY-002).

Benchmarks migration throughput without requiring full app bootstrap (avoids Pinecone import in CI).
Run: uv run pytest tests/load/test_phase5_endpoints.py -v
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.phase5_migration_service import Phase5MigrationService
from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_COMPLETED
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


def _seed_projects(count: int) -> list[CarouselProjectModel]:
    now = datetime.now(UTC)
    projects: list[CarouselProjectModel] = []
    for index in range(count):
        projects.append(
            CarouselProjectModel(
                id=str(uuid.uuid4()),
                topic=f"Topic {index}",
                audience="Developers",
                niche="Tech",
                title=f"Title {index}",
                slides_config="5 slides",
                aspect_ratio="4:5",
                language="en",
                theme="auto",
                image_style="comic_neon",
                status=CAROUSEL_STATUS_COMPLETED,
                caption=f"Sample caption {index} for load testing migration throughput.",
                created_at=now,
                updated_at=now,
            )
        )
    return projects


@pytest.mark.asyncio
async def test_migration_handles_batch_load(session: AsyncSession) -> None:
    """DEPLOY-002: Migration service processes 50 projects within time budget."""
    batch_size = 50
    session.add_all(_seed_projects(batch_size))
    await session.commit()

    start = time.perf_counter()
    report = await Phase5MigrationService().run(session, dry_run=False)
    elapsed = time.perf_counter() - start

    assert report.creative_briefs_updated == batch_size
    assert report.persona_created is True
    assert report.rubric_created is True
    assert elapsed < 5.0, f"Migration of {batch_size} projects took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_concurrent_brief_building() -> None:
    """DEPLOY-002: Concurrent brief building completes within time budget."""
    now = datetime.now(UTC)
    projects = [
        CarouselProjectModel(
            id=str(uuid.uuid4()),
            topic=f"Concurrent {index}",
            audience="Devs",
            niche="Tech",
            slides_config="3 slides",
            aspect_ratio="4:5",
            language="en",
            theme="auto",
            image_style="comic_neon",
            status=CAROUSEL_STATUS_COMPLETED,
            created_at=now,
            updated_at=now,
        )
        for index in range(100)
    ]

    from rag_backend.application.services.phase5_migration_service import build_creative_brief

    start = time.perf_counter()

    async def build_one(project: CarouselProjectModel) -> str:
        await asyncio.sleep(0)
        return build_creative_brief(project)

    briefs = await asyncio.gather(*[build_one(project) for project in projects])
    elapsed = time.perf_counter() - start

    assert len(briefs) == 100
    assert all("Concurrent" in brief for brief in briefs)
    assert elapsed < 2.0, f"100 concurrent brief builds took {elapsed:.2f}s"
