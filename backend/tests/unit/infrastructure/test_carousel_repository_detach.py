"""Carousel delete detaches its published blog row (AE-0296 / AE-0422).

Scenario: Deleting a carousel project reverts its published blog row to draft
(see features/blog_post_management_ae0296.feature and
backend/tests/features/blog_no_carousel_slides_ae0422.feature).

AE-0422: a carousel save no longer creates a blog row, so these tests insert the
carousel-origin row explicitly before deleting the project.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.models import CarouselProject, CarouselTheme
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel


def _project() -> CarouselProject:
    return CarouselProject(
        topic="Detach test",
        audience="Testers",
        niche="QA",
        theme=CarouselTheme.AI_COMPETITION,
    )


async def _insert_carousel_blog_row(
    db_session: AsyncSession,
    project_id: str,
    status: BlogPostStatus,
) -> BlogPostModel:
    """Insert an ``origin='carousel'`` blog row for the project (explicit row)."""
    row = BlogPostModel.from_entity(
        {
            "id": str(uuid4()),
            "project_id": project_id,
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": "Detach test",
            "slug": f"carousel-{project_id}",
            "status": status.value,
            "content": {"markdown": "# Blog body", "translations": {}},
        }
    )
    db_session.add(row)
    await db_session.flush()
    return row


@pytest.mark.unit
class TestDeleteProjectDetachesBlogRow:
    async def test_published_blog_row_flips_to_draft_on_project_delete(
        self, carousel_repository, db_session
    ) -> None:
        created = await carousel_repository.create_project(_project())

        row = await _insert_carousel_blog_row(
            db_session, str(created.id), BlogPostStatus.PUBLISHED
        )
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

    async def test_carousel_save_does_not_create_a_blog_row(
        self, carousel_repository, db_session
    ) -> None:
        project = _project()
        project.blog_markdown = "# Blog body"
        created = await carousel_repository.create_project(project)

        rows = (
            (
                await db_session.execute(
                    select(BlogPostModel).where(
                        BlogPostModel.project_id == str(created.id)
                    )
                )
            )
            .scalars()
            .all()
        )
        assert rows == []

    @pytest.mark.parametrize(
        "untouched_status",
        [BlogPostStatus.DRAFT, BlogPostStatus.ARCHIVED],
    )
    async def test_non_published_blog_row_is_left_untouched(
        self, carousel_repository, db_session, untouched_status: BlogPostStatus
    ) -> None:
        created = await carousel_repository.create_project(_project())
        row = await _insert_carousel_blog_row(
            db_session, str(created.id), untouched_status
        )
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
        assert row_after.status == untouched_status.value
        assert row_after.published_at is None
        assert row_after.lock_version == initial_lock_version
