"""Unit tests for blog post repository (PERF-001)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.infrastructure.database.blog_post_repository import BlogPostRepository
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_summaries_with_search(db_session: AsyncSession) -> None:
    # Scenario: Blog post list supports search and pagination
    repo = BlogPostRepository()
    db_session.add(
        BlogPostModel.from_entity({
            "title": "AI Security",
            "slug": "ai-security",
            "author_id": "u1",
        })
    )
    db_session.add(
        BlogPostModel.from_entity({
            "title": "Cloud Tips",
            "slug": "cloud-tips",
            "author_id": "u1",
        })
    )
    await db_session.commit()

    posts, total = await repo.list_summaries(
        db_session, search="security", limit=10, offset=0
    )
    assert total == 1
    assert posts[0].title == "AI Security"
