"""Unit tests for OptimisticLockService (WF-005)."""

# Gherkin: tests/features/phase3_workflow_collaboration.feature
# Scenario: Version conflict on blog post update

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.optimistic_lock_service import (
    CarouselVersionBumpParams,
    OptimisticLockService,
)
from rag_backend.domain.constants.optimistic_locking import (
    ERR_LOCK_HELD_BY_OTHER,
    ERR_VERSION_CONFLICT,
    LOCK_CONTENT_TYPE_BLOG_POST,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


@pytest.mark.asyncio
async def test_check_version_raises_on_conflict() -> None:
    service = OptimisticLockService()
    with pytest.raises(ValueError, match=ERR_VERSION_CONFLICT):
        await service.check_version(current_version=2, expected_version=1)


@pytest.mark.asyncio
async def test_apply_versioned_update_increments_lock(db_session: AsyncSession) -> None:
    """Gherkin: Version conflict on blog post update."""
    post = BlogPostModel(
        title="Version Test",
        slug="version-test-atomic",
        status="draft",
        lock_version=2,
    )
    db_session.add(post)
    await db_session.flush()

    service = OptimisticLockService()
    await service.apply_versioned_update(
        db_session,
        post_id=str(post.id),
        expected_version=2,
        values={"title": "Updated Title"},
    )
    await db_session.refresh(post)
    assert post.title == "Updated Title"
    assert post.lock_version == 3


@pytest.mark.asyncio
async def test_apply_versioned_update_raises_on_stale_version(
    db_session: AsyncSession,
) -> None:
    post = BlogPostModel(
        title="Stale Version",
        slug="stale-version-test",
        status="draft",
        lock_version=2,
    )
    db_session.add(post)
    await db_session.flush()

    service = OptimisticLockService()
    with pytest.raises(ValueError, match=ERR_VERSION_CONFLICT):
        await service.apply_versioned_update(
            db_session,
            post_id=str(post.id),
            expected_version=1,
            values={"title": "Should Fail"},
        )


@pytest.mark.asyncio
async def test_acquire_lock_blocks_other_user(db_session: AsyncSession) -> None:
    service = OptimisticLockService()
    await service.acquire_lock(
        db_session,
        content_id="post-1",
        content_type=LOCK_CONTENT_TYPE_BLOG_POST,
        user_id="user-a",
        user_name="Alice",
    )
    with pytest.raises(ValueError, match=ERR_LOCK_HELD_BY_OTHER):
        await service.acquire_lock(
            db_session,
            content_id="post-1",
            content_type=LOCK_CONTENT_TYPE_BLOG_POST,
            user_id="user-b",
            user_name="Bob",
        )


@pytest.mark.asyncio
async def test_bump_carousel_version_increments_lock(db_session: AsyncSession) -> None:
    """Gherkin: Optimistic lock conflict on concurrent resume."""
    project = CarouselProjectModel(
        topic="Carousel lock",
        audience="Devs",
        niche="AI",
        lock_version=2,
    )
    db_session.add(project)
    await db_session.flush()

    service = OptimisticLockService()
    new_version = await service.bump_carousel_version(
        db_session,
        CarouselVersionBumpParams(
            project_id=str(project.id),
            expected_version=2,
        ),
    )
    await db_session.refresh(project)
    assert new_version == 3
    assert project.lock_version == 3


@pytest.mark.asyncio
async def test_bump_carousel_version_raises_on_stale_version(
    db_session: AsyncSession,
) -> None:
    project = CarouselProjectModel(
        topic="Stale carousel lock",
        audience="Devs",
        niche="AI",
        lock_version=3,
    )
    db_session.add(project)
    await db_session.flush()

    service = OptimisticLockService()
    with pytest.raises(ValueError, match=ERR_VERSION_CONFLICT):
        await service.bump_carousel_version(
            db_session,
            CarouselVersionBumpParams(
                project_id=str(project.id),
                expected_version=2,
            ),
        )
