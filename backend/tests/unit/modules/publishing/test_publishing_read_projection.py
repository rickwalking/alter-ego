"""Unit tests for the publishing read projection ports (AE-0131).

These tests prove the behavior-preserving extraction of the public/editor READ
surfaces — the carousel ``/blog`` (+lang) projection, the content-calendar, the
workflow-board, the editorial-analytics, and the blog-post CRUD persistence rows
— behind the publishing read port + the read ACL (the sole carousel/blog ORM
read seam):

* the carousel-blog projection sources the body + the 404 signal SOLELY from the
  AE-0127/AE-0163 ``origin='carousel'`` ``blog_posts`` row (the embedded carousel
  ``blog_markdown`` column is no longer read), resolving title/subtitle from the
  row with the project title/topic/subtitle fallback (byte-identical fields), and
  maps an absent/body-less row to ``None`` (the route's legacy 404);
* the localized projection reproduces the legacy en/pt title/subtitle fallback
  chain and the ``available_languages`` list;
* the calendar/board/analytics projections aggregate exactly the legacy rows with
  the legacy filters, ordering, and field mapping;
* the blog-CRUD port builds/loads/lists the blog rows the routes stage;
* the service forwards to the read/blog-CRUD ports and raises a clear error when
  a read use case has no wired port.

Deterministic; no live keys. SQLite in-memory backs the ORM-touching reads.
Behavior-preserving extraction; the live-response diff is asserted by the AE-0125
safety net (Gherkin not applicable — see ticket AE-0131).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.domain.constants.blog_post import BlogPostOrigin
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_PENDING,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.publishing import (
    AnalyticsQuery,
    BlogListQuery,
    BoardQuery,
    CalendarQuery,
    CarouselRepository,
    PublishingPorts,
    PublishingReadAcl,
    PublishingService,
)
from rag_backend.modules.publishing.infrastructure.publishing_port_adapters import (
    AclBlogPostCrudAdapter,
    AclPublishingReadAdapter,
)
from rag_backend.modules.publishing.infrastructure.read_projection_helpers import (
    extract_first_paragraph,
    extract_title_and_subtitle,
    resolve_blog_body,
)

_BLOG_PT = "# Title PT: Subtitle PT\n\nDeterministic body."
_BLOG_EN = "# Title EN: Subtitle EN\n\nDeterministic body EN."


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """SQLite in-memory session with the ORM schema created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _carousel_entity() -> CarouselProject:
    """Build a public completed carousel entity with embedded blog content."""
    return CarouselProject(
        topic="Fixture topic",
        audience="Fixture audience",
        niche="FIXTURE",
        is_public=True,
        title="Embedded Title",
        subtitle="Embedded Subtitle",
        blog_markdown=_BLOG_PT,
        blog_translations={"pt": _BLOG_PT, "en": _BLOG_EN},
    )


# ==============================================================================
# Pure markdown helpers (byte-identical to the legacy route helpers)
# ==============================================================================
class TestReadProjectionHelpers:
    """The markdown title/subtitle/body helpers replicate the legacy logic."""

    def test_extract_title_and_subtitle_splits_heading(self) -> None:
        """Scenario: a ``# Title: Subtitle`` heading splits on the colon."""
        assert extract_title_and_subtitle("# Foo: Bar\n\nbody") == ("Foo", "Bar")

    def test_extract_title_and_subtitle_without_separator(self) -> None:
        """Scenario: a heading without a colon yields a title and no subtitle."""
        assert extract_title_and_subtitle("# Foo\n\nbody") == ("Foo", None)

    def test_extract_title_and_subtitle_no_heading(self) -> None:
        """Scenario: no leading ``# `` heading yields no title/subtitle."""
        assert extract_title_and_subtitle("body only") == (None, None)

    def test_extract_first_paragraph_skips_headings(self) -> None:
        """Scenario: the first non-heading paragraph is returned, truncated."""
        assert extract_first_paragraph("# H\n\nFirst para\n\nSecond") == "First para"

    def test_resolve_blog_body_sources_from_row(self) -> None:
        """Scenario: the body is sourced from the origin='carousel' row (AE-0163)."""
        row = BlogPostModel.from_entity({
            "title": "Row",
            "slug": "row",
            "content": {"markdown": "ROW BODY"},
        })
        assert resolve_blog_body(row) == "ROW BODY"

    def test_resolve_blog_body_none_when_no_row_or_body(self) -> None:
        """Scenario: an absent row or empty body yields None (AE-0163, no fallback).

        The embedded ``blog_markdown`` column is no longer read; the body comes
        solely from the dual-write/backfill row.
        """
        assert resolve_blog_body(None) is None
        row = BlogPostModel.from_entity({"title": "R", "slug": "r", "content": {}})
        assert resolve_blog_body(row) is None


# ==============================================================================
# Carousel-blog projection (AE-0163: sourced solely from the origin='carousel' row)
# ==============================================================================
class TestCarouselBlogProjection:
    """The carousel-blog projection mirrors the legacy media-route fields."""

    @staticmethod
    def _add_carousel_row(
        session: AsyncSession,
        project: CarouselProject,
        *,
        title: str,
        excerpt: str | None,
        markdown: str,
    ) -> None:
        """Insert the canonical origin='carousel' row (AE-0127/AE-0163 shape)."""
        session.add(
            BlogPostModel.from_entity({
                "project_id": str(project.id),
                "origin": BlogPostOrigin.CAROUSEL.value,
                "title": title,
                "slug": f"carousel-{project.id}",
                "excerpt": excerpt,
                "content": {"markdown": markdown},
            })
        )

    @pytest.mark.asyncio
    async def test_no_row_returns_none(self, db_session: AsyncSession) -> None:
        """Scenario: with no origin='carousel' row, the projection is None (404).

        The embedded ``blog_markdown`` column is no longer read (AE-0163); the body
        + 404 signal come solely from the dual-write/backfill row.
        """
        acl = PublishingReadAcl(db_session)
        assert await acl.project_carousel_blog(_carousel_entity()) is None

    @pytest.mark.asyncio
    async def test_row_supplies_body_and_title(self, db_session: AsyncSession) -> None:
        """Scenario: the origin='carousel' row supplies the body + title/subtitle."""
        project = _carousel_entity()
        self._add_carousel_row(
            db_session,
            project,
            title="Backfill Title",
            excerpt="Backfill Subtitle",
            markdown="BACKFILL BODY",
        )
        await db_session.commit()
        acl = PublishingReadAcl(db_session)
        projection = await acl.project_carousel_blog(project)
        assert projection is not None
        assert projection.markdown == "BACKFILL BODY"
        assert projection.title == "Backfill Title"
        assert projection.subtitle == "Backfill Subtitle"

    @pytest.mark.asyncio
    async def test_row_empty_title_excerpt_falls_back_to_project(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: the row supplies the body; empty title/excerpt fall back to the
        project title/subtitle (the AE-0127 row shape — excerpt NULL — preserved)."""
        project = _carousel_entity()
        self._add_carousel_row(
            db_session,
            project,
            title="",
            excerpt="",
            markdown="BACKFILL BODY",
        )
        await db_session.commit()
        acl = PublishingReadAcl(db_session)
        projection = await acl.project_carousel_blog(project)
        assert projection is not None
        assert projection.markdown == "BACKFILL BODY"  # body from the row
        assert projection.title == "Embedded Title"  # empty row title -> project
        assert projection.subtitle == "Embedded Subtitle"  # empty excerpt -> project

    @pytest.mark.asyncio
    async def test_row_without_body_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: a row with no rendered body maps to ``None`` (the legacy 404)."""
        project = _carousel_entity()
        db_session.add(
            BlogPostModel.from_entity({
                "project_id": str(project.id),
                "origin": BlogPostOrigin.CAROUSEL.value,
                "title": "Bodyless",
                "slug": f"carousel-{project.id}",
                "content": {},
            })
        )
        await db_session.commit()
        acl = PublishingReadAcl(db_session)
        assert await acl.project_carousel_blog(project) is None

    @pytest.mark.asyncio
    async def test_i18n_en_resolves_title_and_languages(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: the English projection resolves title/subtitle + languages."""
        acl = PublishingReadAcl(db_session)
        projection = await acl.project_carousel_blog_i18n(_carousel_entity(), "en")
        assert projection is not None
        assert projection.markdown == _BLOG_EN
        assert projection.title == "Title EN"
        assert projection.subtitle == "Subtitle EN"
        assert projection.language == "en"
        assert projection.available_languages == ["pt", "en"]

    @pytest.mark.asyncio
    async def test_i18n_absent_language_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: a language with no blog body maps to ``None``."""
        project = _carousel_entity()
        project.blog_markdown = None
        project.blog_translations = {"pt": _BLOG_PT}
        acl = PublishingReadAcl(db_session)
        assert await acl.project_carousel_blog_i18n(project, "en") is None


# ==============================================================================
# Calendar / board / analytics projections
# ==============================================================================
class TestAggregateProjections:
    """The calendar/board/analytics projections aggregate the legacy rows."""

    @pytest.mark.asyncio
    async def test_calendar_includes_scheduled_blog(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: a scheduled blog post appears as a calendar item."""
        scheduled = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)
        db_session.add(
            BlogPostModel.from_entity({
                "title": "Scheduled Post",
                "slug": "scheduled-post",
                "status": "scheduled",
                "content": {},
                "scheduled_publish_at": scheduled,
            })
        )
        await db_session.commit()
        acl = PublishingReadAcl(db_session)
        projection = await acl.project_calendar(
            CalendarQuery(
                start=datetime(2026, 6, 1, tzinfo=UTC),
                end=datetime(2026, 6, 30, tzinfo=UTC),
            ),
        )
        titles = [item.title for item in projection.items]
        assert "Scheduled Post" in titles
        item = next(i for i in projection.items if i.title == "Scheduled Post")
        assert item.content_type == "blog_post"
        assert item.is_scheduled is True

    @pytest.mark.asyncio
    async def test_board_groups_project_by_phase(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: a non-pending carousel groups into its phase column."""
        db_session.add(
            CarouselProjectModel(
                id=str(uuid4()),
                topic="Board topic",
                audience="aud",
                niche="N",
                theme="ai_competition",
                current_phase=PHASE_CONTENT,
                phase_status=PHASE_STATUS_AWAITING_HUMAN,
            )
        )
        await db_session.commit()
        acl = PublishingReadAcl(db_session)
        projection = await acl.project_board(BoardQuery())
        columns = {col.phase: col for col in projection.columns}
        content_cards = columns[PHASE_CONTENT].cards
        assert content_cards
        assert content_cards[0].topic == "Board topic"

    @pytest.mark.asyncio
    async def test_board_excludes_pending_phase_status(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: a pending-phase carousel is excluded from the board."""
        db_session.add(
            CarouselProjectModel(
                id=str(uuid4()),
                topic="Pending topic",
                audience="aud",
                niche="N",
                theme="ai_competition",
                current_phase=PHASE_CONTENT,
                phase_status=PHASE_STATUS_PENDING,
            )
        )
        await db_session.commit()
        acl = PublishingReadAcl(db_session)
        projection = await acl.project_board(BoardQuery())
        topics = [card.topic for col in projection.columns for card in col.cards]
        assert "Pending topic" not in topics

    @pytest.mark.asyncio
    async def test_analytics_counts_drafts(self, db_session: AsyncSession) -> None:
        """Scenario: analytics counts a draft blog post in the summary."""
        db_session.add(
            BlogPostModel.from_entity({
                "title": "Draft Post",
                "slug": "draft-post",
                "status": "draft",
                "content": {},
            })
        )
        await db_session.commit()
        acl = PublishingReadAcl(db_session)
        projection = await acl.project_analytics(AnalyticsQuery(weeks=4))
        assert projection.summary.total_posts == 1
        assert projection.summary.draft_count == 1
        assert len(projection.velocity_by_week) == 4


# ==============================================================================
# Blog-CRUD port + service forwarding
# ==============================================================================
class TestBlogCrudPortAndService:
    """The blog-CRUD port and the service forward to the read ACL."""

    @pytest.mark.asyncio
    async def test_new_get_list_round_trip(self, db_session: AsyncSession) -> None:
        """Scenario: new_post builds a row that get_post/list_summaries return."""
        acl = PublishingReadAcl(db_session)
        post = acl.new_post({"title": "CRUD", "slug": "crud", "content": {}})
        db_session.add(post)
        await db_session.commit()
        loaded = await acl.get_post(str(post.id))
        assert loaded is not None
        assert loaded.title == "CRUD"
        posts, total = await acl.list_summaries(BlogListQuery(limit=10))
        assert total == 1
        assert posts[0].slug == "crud"

    @pytest.mark.asyncio
    async def test_service_forwards_to_read_and_crud_ports(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: the service routes projections + CRUD through wired ports."""
        project = _carousel_entity()
        db_session.add(
            BlogPostModel.from_entity({
                "project_id": str(project.id),
                "origin": BlogPostOrigin.CAROUSEL.value,
                "title": "Embedded Title",
                "slug": f"carousel-{project.id}",
                "content": {"markdown": _BLOG_PT},
            })
        )
        await db_session.commit()
        acl = PublishingReadAcl(db_session)
        service = PublishingService(
            carousel_repository=MagicMock(spec=CarouselRepository),
            ports=PublishingPorts(
                read=AclPublishingReadAdapter(acl),
                blog_crud=AclBlogPostCrudAdapter(acl),
            ),
        )
        projection = await service.project_carousel_blog(project)
        assert projection is not None
        assert projection.markdown == _BLOG_PT
        post = service.new_blog_post({"title": "S", "slug": "s", "content": {}})
        assert post.title == "S"

    @pytest.mark.asyncio
    async def test_service_raises_without_read_port(self) -> None:
        """Scenario: a read use case without a wired port raises a clear error."""
        service = PublishingService(
            carousel_repository=MagicMock(spec=CarouselRepository)
        )
        with pytest.raises(RuntimeError):
            await service.project_board(BoardQuery())
        with pytest.raises(RuntimeError):
            service.new_blog_post({})
