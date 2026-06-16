"""Unit tests for the publishing release/visibility/schedule ports (AE-0128).

These tests prove the behavior-preserving extraction of the carousel public
release + the standalone blog visibility/scheduling writes behind publishing
ports + the publishing ACL/owner:

* the release command + service forward to the carousel release port and return
  the updated entity (the byte-identical ``crud.py`` ``is_public`` write);
* the ACL/owner is the sole carousel/blog ORM seam and reproduces the legacy
  field writes exactly (``is_public=True`` / ``current_phase=published`` on the
  entity + ORM row + the single commit; the blog publish/unpublish status writes;
  the schedule delegation to the existing scheduled-publish service);
* the ACL-backed port adapters delegate to the ACL;
* the service raises a clear error when a write use case has no wired port.

Behavior-preserving extraction; the live-response diff is asserted by the AE-0125
safety net (Gherkin not applicable — see ticket AE-0128).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.carousel_workflow import PHASE_PUBLISHED
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.modules.publishing import (
    AclBlogScheduleAdapter,
    AclBlogVisibilityAdapter,
    AclCarouselReleaseAdapter,
    CarouselReleaseCommand,
    CarouselRepository,
    LegacyPublishingAcl,
    PublishingAdapters,
    PublishingPorts,
    PublishingService,
    bootstrap_module,
)


def _make_blog_post(status: str) -> BlogPostModel:
    """Build a transient blog ORM row in the given status."""
    return BlogPostModel.from_entity({
        "title": "Fixture",
        "slug": "fixture",
        "status": status,
        "content": {},
    })


class TestCarouselReleaseHandlerAndService:
    """Scenario: the release command forwards to the release port."""

    @pytest.mark.asyncio
    async def test_release_carousel_forwards_to_port_and_returns_entity(self) -> None:
        project = CarouselProject(topic="AI", audience="devs", niche="tech")
        updated = CarouselProject(topic="AI", audience="devs", niche="tech")
        release_port = AsyncMock()
        release_port.release_public.return_value = updated
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            ports=PublishingPorts(carousel_release=release_port),
        )

        result = await service.release_carousel(
            CarouselReleaseCommand(project=project, project_id=str(project.id)),
        )

        release_port.release_public.assert_awaited_once_with(project, str(project.id))
        assert result is updated

    @pytest.mark.asyncio
    async def test_release_carousel_without_port_raises(self) -> None:
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
        )
        with pytest.raises(RuntimeError):
            await service.release_carousel(
                CarouselReleaseCommand(project=object(), project_id="p1"),
            )


class TestBlogVisibilityScheduleService:
    """Scenario: blog visibility/schedule use cases forward to their ports."""

    @pytest.mark.asyncio
    async def test_publish_unpublish_forward_to_visibility_port(self) -> None:
        visibility = AsyncMock()
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            ports=PublishingPorts(blog_visibility=visibility),
        )
        post = object()

        await service.publish_blog(post)
        await service.unpublish_blog(post)

        visibility.mark_published.assert_awaited_once_with(post)
        visibility.mark_unpublished.assert_awaited_once_with(post)

    @pytest.mark.asyncio
    async def test_schedule_and_due_sweep_forward_to_schedule_port(self) -> None:
        schedule = AsyncMock()
        schedule.process_due_posts.return_value = 3
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            ports=PublishingPorts(blog_schedule=schedule),
        )
        post = object()
        when = datetime(2026, 7, 1, tzinfo=UTC)

        await service.schedule_blog(post, when)
        published = await service.process_due_blog_posts()

        schedule.schedule_publish.assert_awaited_once_with(post, when)
        assert published == 3

    @pytest.mark.asyncio
    async def test_missing_ports_raise(self) -> None:
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
        )
        with pytest.raises(RuntimeError):
            await service.publish_blog(object())
        with pytest.raises(RuntimeError):
            await service.schedule_blog(object(), datetime(2026, 7, 1, tzinfo=UTC))


class TestLegacyPublishingAcl:
    """Scenario: the ACL/owner reproduces the legacy writes byte-for-byte."""

    @pytest.mark.asyncio
    async def test_release_public_writes_entity_orm_and_commits(self) -> None:
        project = CarouselProject(topic="AI", audience="devs", niche="tech")
        updated = CarouselProject(topic="AI", audience="devs", niche="tech")
        repo = AsyncMock(spec=CarouselRepository)
        repo.update_project.return_value = updated
        model = MagicMock()
        session = AsyncMock()
        session.get.return_value = model
        acl = LegacyPublishingAcl(session, repo)

        result = await acl.release_public(project, str(project.id))

        # Entity write mirrors the legacy crud sequence.
        assert project.is_public is True
        assert project.current_phase == PHASE_PUBLISHED
        repo.update_project.assert_awaited_once_with(project)
        # ORM row write + single commit.
        assert model.is_public is True
        assert model.current_phase == PHASE_PUBLISHED
        session.commit.assert_awaited_once()
        assert result is updated

    @pytest.mark.asyncio
    async def test_release_public_absent_model_skips_commit(self) -> None:
        project = CarouselProject(topic="AI", audience="devs", niche="tech")
        repo = AsyncMock(spec=CarouselRepository)
        repo.update_project.return_value = project
        session = AsyncMock()
        session.get.return_value = None
        acl = LegacyPublishingAcl(session, repo)

        await acl.release_public(project, str(project.id))

        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_release_public_rejects_non_carousel(self) -> None:
        acl = LegacyPublishingAcl(AsyncMock(), AsyncMock(spec=CarouselRepository))
        with pytest.raises(TypeError):
            await acl.release_public(object(), "p1")

    @pytest.mark.asyncio
    async def test_mark_published_sets_status_and_stamps(self) -> None:
        post = _make_blog_post(BlogPostStatus.APPROVED.value)
        post.scheduled_publish_at = datetime(2026, 7, 1, tzinfo=UTC)
        acl = LegacyPublishingAcl(AsyncMock(), AsyncMock(spec=CarouselRepository))

        await acl.mark_published(post)

        assert post.status == BlogPostStatus.PUBLISHED.value
        assert post.published_at is not None
        assert post.scheduled_publish_at is None

    @pytest.mark.asyncio
    async def test_mark_unpublished_reverts_to_draft(self) -> None:
        post = _make_blog_post(BlogPostStatus.PUBLISHED.value)
        post.published_at = datetime(2026, 7, 1, tzinfo=UTC)
        post.submitted_for_review_at = datetime(2026, 6, 1, tzinfo=UTC)
        acl = LegacyPublishingAcl(AsyncMock(), AsyncMock(spec=CarouselRepository))

        await acl.mark_unpublished(post)

        assert post.status == BlogPostStatus.DRAFT.value
        assert post.published_at is None
        assert post.submitted_for_review_at is None

    @pytest.mark.asyncio
    async def test_blog_visibility_rejects_non_blog_row(self) -> None:
        acl = LegacyPublishingAcl(AsyncMock(), AsyncMock(spec=CarouselRepository))
        with pytest.raises(TypeError):
            await acl.mark_published(object())

    @pytest.mark.asyncio
    async def test_schedule_delegates_to_scheduler(self) -> None:
        post = _make_blog_post(BlogPostStatus.APPROVED.value)
        scheduler = AsyncMock()
        session = AsyncMock()
        acl = LegacyPublishingAcl(
            session, AsyncMock(spec=CarouselRepository), scheduler
        )
        when = datetime(2026, 7, 1, tzinfo=UTC)

        await acl.schedule_publish(post, when)

        scheduler.schedule_post.assert_awaited_once_with(session, post, when)

    @pytest.mark.asyncio
    async def test_process_due_posts_delegates_to_scheduler(self) -> None:
        scheduler = AsyncMock()
        scheduler.process_due_posts.return_value = 2
        acl = LegacyPublishingAcl(
            AsyncMock(), AsyncMock(spec=CarouselRepository), scheduler
        )

        assert await acl.process_due_posts() == 2

    @pytest.mark.asyncio
    async def test_schedule_without_scheduler_raises(self) -> None:
        acl = LegacyPublishingAcl(AsyncMock(), AsyncMock(spec=CarouselRepository))
        with pytest.raises(RuntimeError):
            await acl.schedule_publish(_make_blog_post("approved"), datetime.now(UTC))


class TestAclPortAdapters:
    """Scenario: the ACL-backed port adapters delegate to the ACL."""

    @pytest.mark.asyncio
    async def test_release_adapter_delegates(self) -> None:
        acl = AsyncMock()
        acl.release_public.return_value = "updated"
        adapter = AclCarouselReleaseAdapter(acl)

        result = await adapter.release_public("project", "p1")

        acl.release_public.assert_awaited_once_with("project", "p1")
        assert result == "updated"

    @pytest.mark.asyncio
    async def test_visibility_adapter_delegates(self) -> None:
        acl = AsyncMock()
        adapter = AclBlogVisibilityAdapter(acl)

        await adapter.mark_published("post")
        await adapter.mark_unpublished("post")

        acl.mark_published.assert_awaited_once_with("post")
        acl.mark_unpublished.assert_awaited_once_with("post")

    @pytest.mark.asyncio
    async def test_schedule_adapter_delegates(self) -> None:
        acl = AsyncMock()
        acl.process_due_posts.return_value = 1
        adapter = AclBlogScheduleAdapter(acl)
        when = datetime(2026, 7, 1, tzinfo=UTC)

        await adapter.schedule_publish("post", when)
        published = await adapter.process_due_posts()

        acl.schedule_publish.assert_awaited_once_with("post", when)
        assert published == 1


class TestBootstrapWiresAclPorts:
    """Scenario: bootstrap wires the ACL-backed ports onto the service."""

    @pytest.mark.asyncio
    async def test_bootstrap_with_acl_routes_release_through_acl(self) -> None:
        project = CarouselProject(topic="AI", audience="devs", niche="tech")
        updated = CarouselProject(topic="AI", audience="devs", niche="tech")
        repo = AsyncMock(spec=CarouselRepository)
        repo.update_project.return_value = updated
        session = AsyncMock()
        session.get.return_value = MagicMock()
        acl = LegacyPublishingAcl(session, repo)
        adapters = PublishingAdapters(
            carousel_repository=repo,
            unit_of_work=AsyncMock(),
            publishing_acl=acl,
        )

        module = bootstrap_module(platform=MagicMock(), adapters=adapters)
        result = await module.service.release_carousel(
            CarouselReleaseCommand(project=project, project_id=str(project.id)),
        )

        assert result is updated
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bootstrap_without_acl_leaves_release_unwired(self) -> None:
        adapters = PublishingAdapters(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            unit_of_work=AsyncMock(),
        )

        module = bootstrap_module(platform=MagicMock(), adapters=adapters)

        with pytest.raises(RuntimeError):
            await module.service.release_carousel(
                CarouselReleaseCommand(project=object(), project_id=str(uuid4())),
            )
