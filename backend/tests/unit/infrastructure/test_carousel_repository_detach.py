"""Carousel delete detaches its published blog row (AE-0296).

Scenario: Deleting a carousel project reverts its published blog row to draft
(see features/blog_post_management_ae0296.feature).
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.models import CarouselProject, CarouselTheme
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel


def _project_with_blog() -> CarouselProject:
    return CarouselProject(
        topic="Detach test",
        audience="Testers",
        niche="QA",
        theme=CarouselTheme.AI_COMPETITION,
        blog_markdown="# Blog body",
    )


@pytest.mark.unit
class TestDeleteProjectDetachesBlogRow:
    async def test_published_blog_row_flips_to_draft_on_project_delete(
        self, carousel_repository, db_session
    ) -> None:
        created = await carousel_repository.create_project(_project_with_blog())

        row = (
            (
                await db_session.execute(
                    select(BlogPostModel).where(
                        BlogPostModel.project_id == str(created.id)
                    )
                )
            )
            .scalars()
            .one()
        )
        assert row.origin == BlogPostOrigin.CAROUSEL.value
        assert row.status == BlogPostStatus.PUBLISHED.value
        row.published_at = datetime.now(UTC)
        initial_lock_version = row.lock_version
        row_id = row.id
        await db_session.flush()

        deleted = await carousel_repository.delete_project(created.id)
        assert deleted is True

        db_session.expire_all()
        row_after = (
            (
                await db_session.execute(
                    select(BlogPostModel).where(BlogPostModel.id == row_id)
                )
            )
            .scalars()
            .one()
        )
        assert row_after.status == BlogPostStatus.DRAFT.value
        assert row_after.published_at is None
        assert row_after.submitted_for_review_at is None
        assert row_after.lock_version == initial_lock_version + 1

    async def test_non_published_blog_row_is_left_untouched(
        self, carousel_repository, db_session
    ) -> None:
        created = await carousel_repository.create_project(_project_with_blog())
        row = (
            (
                await db_session.execute(
                    select(BlogPostModel).where(
                        BlogPostModel.project_id == str(created.id)
                    )
                )
            )
            .scalars()
            .one()
        )
        row.status = BlogPostStatus.ARCHIVED.value
        initial_lock_version = row.lock_version
        row_id = row.id
        await db_session.flush()

        assert await carousel_repository.delete_project(created.id) is True

        db_session.expire_all()
        row_after = (
            (
                await db_session.execute(
                    select(BlogPostModel).where(BlogPostModel.id == row_id)
                )
            )
            .scalars()
            .one()
        )
        assert row_after.status == BlogPostStatus.ARCHIVED.value
        assert row_after.lock_version == initial_lock_version
