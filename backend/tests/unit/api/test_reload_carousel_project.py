"""``reload_carousel_project``: the stored project, never a lazy load.

Feature file: tests/features/carousel_checklist_wysiwyg.feature
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.api.dependencies.carousel_access import reload_carousel_project
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


@pytest.mark.asyncio
async def test_reload_reads_an_expired_row_without_a_lazy_load(
    test_engine: AsyncEngine,
) -> None:
    """Scenario: The start response carries the checklist slides."""
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    project_id = str(uuid.uuid4())
    async with maker() as db:
        row = CarouselProjectModel(
            id=project_id,
            topic="T",
            audience="A",
            niche="N",
            slide_layout_strategy="save_checklist",
        )
        db.add(row)
        await db.commit()
        db.expire(row)

        project = await reload_carousel_project(db, uuid.UUID(project_id))
        missing = await reload_carousel_project(db, uuid.uuid4())

        await db.execute(
            delete(CarouselProjectModel).where(CarouselProjectModel.id == project_id)
        )
        await db.commit()

    assert project is not None
    assert project.slide_layout_strategy == "save_checklist"
    assert missing is None
