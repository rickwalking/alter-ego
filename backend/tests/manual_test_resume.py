"""Test slide persistence and retrieval across sessions."""

import asyncio
import os

os.environ["SECRET_KEY"] = "test-key"

from rag_backend.application.services.carousel.editorial_visual_pipeline import (
    ensure_slides_from_outline,
)
from rag_backend.infrastructure.database.config import get_session_maker, init_db
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)


async def main():
    await init_db("postgresql+asyncpg://rag_user:rag_password@postgres:5432/rag_db")
    factory = get_session_maker()

    pid = "191223a4-9499-4e66-84d6-e78bdee4e695"

    async with factory() as db1:
        project = await db1.get(CarouselProjectModel, pid)
        assert project is not None, "Project not found"
        print(f"Project: {project.id}")

        from sqlalchemy import delete

        await db1.execute(
            delete(CarouselSlideModel).where(CarouselSlideModel.project_id == pid)
        )
        await db1.commit()

        for i in range(3):
            slide = CarouselSlideModel(
                project_id=pid,
                slide_number=i + 1,
                slide_type="content" if i > 0 else "intro",
                heading=f"Slide {i + 1} heading",
                body=f"Body for slide {i + 1}",
                image_prompt=f"Editorial illustration for Slide {i + 1} heading",
            )
            db1.add(slide)

        await db1.commit()
        print("Session 1: Created 3 slides and committed")

    async with factory() as db2:
        slides = await ensure_slides_from_outline(
            db2,
            pid,
            [
                {"slide_index": 1, "title": "Test", "key_points": ["Point 1"]},
                {"slide_index": 2, "title": "Slide 2", "key_points": ["Point 2"]},
            ],
        )
        print(f"Session 2: ensure_slides_from_outline returned {len(slides)} slides")
        for s in slides:
            print(f"  Slide {s.slide_number}: type={s.slide_type} heading={s.heading}")
            print(f"    image_prompt: {s.image_prompt!r}")


if __name__ == "__main__":
    asyncio.run(main())
