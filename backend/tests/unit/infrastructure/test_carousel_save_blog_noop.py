"""Carousel saves never touch blog posts (AE-0422).

Scenarios (backend/tests/features/blog_no_carousel_slides_ae0422.feature):

* Saving a carousel without a blog row does not create one.
* Saving a carousel does not overwrite an existing row.
* Saving a hidden post does not re-publish it.

The delete-time detach (deleting a carousel still drafts its blog row) is covered
by ``test_carousel_repository_detach.py``.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.models import CarouselProject, CarouselTheme
from rag_backend.infrastructure.database.distribution_home import (
    DISTRIBUTION_CAPTION_KEY,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

_LEGACY_CONTENT = {"markdown": "# legacy body", "translations": {"en": "# legacy EN"}}
_HIDDEN_MARKER = {"at": "2026-10-18T00:00:00Z", "reason": "old-pipeline slide post"}


def _project(caption: str = "a caption") -> CarouselProject:
    return CarouselProject(
        topic="Carousel save test",
        audience="Testers",
        niche="QA",
        theme=CarouselTheme.AI_COMPETITION,
        title="Carousel title",
        blog_markdown="# v1 body",
        caption=caption,
    )


async def _carousel_blog_rows(
    db_session: AsyncSession, project_id: str
) -> list[BlogPostModel]:
    return (
        (
            await db_session.execute(
                select(BlogPostModel).where(
                    BlogPostModel.project_id == project_id,
                    BlogPostModel.origin == BlogPostOrigin.CAROUSEL.value,
                )
            )
        )
        .scalars()
        .all()
    )


async def _insert_carousel_row(
    db_session: AsyncSession,
    project_id: str,
    *,
    status: BlogPostStatus,
    ai_generation_metadata: dict[str, object] | None = None,
) -> BlogPostModel:
    row = BlogPostModel.from_entity(
        {
            "id": str(uuid4()),
            "project_id": project_id,
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": "Existing blog post",
            "slug": f"carousel-{project_id}",
            "status": status.value,
            "content": _LEGACY_CONTENT,
            "ai_generation_metadata": ai_generation_metadata or {},
        }
    )
    db_session.add(row)
    await db_session.flush()
    return row


@pytest.mark.unit
class TestCarouselSaveNeverTouchesBlogPosts:
    async def test_saving_without_a_row_does_not_create_one(
        self, carousel_repository, db_session
    ) -> None:
        created = await carousel_repository.create_project(_project())

        # Save again (update path).
        loaded = await carousel_repository.get_project_by_id(created.id)
        assert loaded is not None
        await carousel_repository.update_project(loaded)

        rows = await _carousel_blog_rows(db_session, str(created.id))
        assert rows == []

    async def test_saving_does_not_overwrite_an_existing_row(
        self, carousel_repository, db_session
    ) -> None:
        created = await carousel_repository.create_project(_project())
        row = await _insert_carousel_row(
            db_session, str(created.id), status=BlogPostStatus.DRAFT
        )
        row_id = row.id
        await db_session.commit()

        loaded = await carousel_repository.get_project_by_id(created.id)
        assert loaded is not None
        await carousel_repository.update_project(loaded)

        db_session.expire_all()
        row_after = (
            await db_session.execute(
                select(BlogPostModel).where(BlogPostModel.id == row_id)
            )
        ).scalar_one()
        assert row_after.content == _LEGACY_CONTENT
        assert row_after.status == BlogPostStatus.DRAFT.value

    async def test_saving_a_hidden_post_does_not_republish_it(
        self, carousel_repository, db_session
    ) -> None:
        created = await carousel_repository.create_project(_project())
        row = await _insert_carousel_row(
            db_session,
            str(created.id),
            status=BlogPostStatus.DRAFT,
            ai_generation_metadata={"hidden_bad_post": _HIDDEN_MARKER},
        )
        row_id = row.id
        await db_session.commit()

        loaded = await carousel_repository.get_project_by_id(created.id)
        assert loaded is not None
        await carousel_repository.update_project(loaded)

        db_session.expire_all()
        row_after = (
            await db_session.execute(
                select(BlogPostModel).where(BlogPostModel.id == row_id)
            )
        ).scalar_one()
        assert row_after.status == BlogPostStatus.DRAFT.value
        assert row_after.ai_generation_metadata["hidden_bad_post"] == _HIDDEN_MARKER

    async def test_saving_still_mirrors_distribution_for_an_existing_row(
        self, carousel_repository, db_session
    ) -> None:
        """ADR-0011 distribution home is preserved (AE-0422 decision).

        Dropping the v1 blog-row upsert keeps the canonical distribution mirror:
        an existing ``origin='carousel'`` row still receives the caption, but its
        ``content`` / ``status`` are never touched.
        """
        created = await carousel_repository.create_project(_project(caption="old"))
        row = await _insert_carousel_row(
            db_session, str(created.id), status=BlogPostStatus.DRAFT
        )
        row_id = row.id
        await db_session.commit()

        loaded = await carousel_repository.get_project_by_id(created.id)
        assert loaded is not None
        loaded.caption = "new caption"
        await carousel_repository.update_project(loaded)

        db_session.expire_all()
        row_after = (
            await db_session.execute(
                select(BlogPostModel).where(BlogPostModel.id == row_id)
            )
        ).scalar_one()
        assert row_after.distribution[DISTRIBUTION_CAPTION_KEY] == "new caption"
        assert row_after.content == _LEGACY_CONTENT
        assert row_after.status == BlogPostStatus.DRAFT.value
