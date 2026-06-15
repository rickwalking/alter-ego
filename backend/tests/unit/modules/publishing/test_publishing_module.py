"""Unit tests for the publishing module skeleton + shims (AE-0126).

These tests prove the behavior-preserving + additive scaffolding:

* the blog + carousel repository ports are **object-identity shims** (re-exports
  of the canonical objects), so existing callers keep resolving;
* the blog status enum, the blog ORM row, and the carousel project entity are
  re-exported object-identically (no new domain strings);
* the facade exposes the documented public API;
* ``bootstrap_module`` wires the module via manual constructor injection (no
  global container);
* the new ``BlogPost`` / ``Publication`` / ``DistributionChannel`` /
  ``PublishingSchedule`` / ``ReleaseState`` value objects are importable, typed,
  and constructible.

Behavior-preserving scaffolding; verified by mypy/lint-imports + this safety net
(see ticket AE-0126 — Gherkin not applicable).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.modules.publishing import (
    BlogPost,
    BlogPostStatus,
    CarouselProject,
    CarouselRepository,
    DistributionChannel,
    DistributionChannelKind,
    Publication,
    PublishingAdapters,
    PublishingModule,
    PublishingSchedule,
    PublishingService,
    ReleasePhase,
    ReleaseState,
    bootstrap_module,
)


class TestRepositoryPortShimIdentity:
    """Scenario: The repository ports re-export to the same canonical objects."""

    def test_carousel_repository_is_identical_object(self) -> None:
        from rag_backend.domain.protocols.repositories import (
            CarouselRepository as Canonical,
        )
        from rag_backend.modules.publishing.domain.ports import (
            CarouselRepository as ModulePort,
        )

        assert Canonical is ModulePort

    def test_blog_post_repository_is_identical_object(self) -> None:
        from rag_backend.infrastructure.database.blog_post_repository import (
            BlogPostRepository as Canonical,
        )
        from rag_backend.modules.publishing.domain.ports import (
            BlogPostRepository as ModulePort,
        )

        assert Canonical is ModulePort


class TestEntityShimIdentity:
    """Scenario: Blog/carousel types re-export to identical objects."""

    def test_blog_status_enum_is_identical_object(self) -> None:
        from rag_backend.domain.constants.blog_post import (
            BlogPostStatus as Canonical,
        )

        assert BlogPostStatus is Canonical

    def test_blog_model_is_identical_object(self) -> None:
        from rag_backend.infrastructure.database.models.blog_post import (
            BlogPostModel as Canonical,
        )
        from rag_backend.modules.publishing import BlogPostModel as Facade

        assert Facade is Canonical

    def test_carousel_project_is_identical_object(self) -> None:
        from rag_backend.domain.models import CarouselProject as Canonical

        assert CarouselProject is Canonical


class TestFacadeSurface:
    """Scenario: The facade exposes the documented public API."""

    def test_public_symbols_exported(self) -> None:
        from rag_backend.modules import publishing as facade

        for name in (
            "PublishingService",
            "PublishingPorts",
            "PublishingAdapters",
            "PublishingModule",
            "BlogPost",
            "Publication",
            "DistributionChannel",
            "DistributionChannelKind",
            "PublishingSchedule",
            "ReleaseState",
            "ReleasePhase",
            "BlogPostStatus",
            "BlogPostModel",
            "BlogPostRepository",
            "CarouselProject",
            "CarouselRepository",
            "bootstrap_module",
        ):
            assert name in facade.__all__
            assert hasattr(facade, name)


class TestDomainValueObjects:
    """Scenario: The new publishing value objects are typed and constructible."""

    def test_blog_post_release_state_derives_from_status(self) -> None:
        post = BlogPost(
            id="bp-1",
            slug="hello-world",
            title="Hello",
            status=BlogPostStatus.PUBLISHED,
            lock_version=1,
        )

        assert post.release_state.phase is ReleasePhase.RELEASED
        assert post.release_state.is_released is True

    def test_release_state_unknown_status_defaults_to_unpublished(self) -> None:
        state = ReleaseState.from_status("not-a-real-status")

        assert state.status is BlogPostStatus.DRAFT
        assert state.phase is ReleasePhase.UNPUBLISHED
        assert state.is_released is False

    def test_release_state_none_status_defaults_to_unpublished(self) -> None:
        state = ReleaseState.from_status(None)

        assert state.phase is ReleasePhase.UNPUBLISHED

    def test_publication_projects_carousel_visibility(self) -> None:
        project = CarouselProject(topic="AI", audience="devs", niche="tech")
        project.is_public = True
        publication = Publication(project=project)

        assert publication.project is project
        assert publication.project_id == project.id
        assert publication.is_public is True

    def test_distribution_channel_defaults_enabled(self) -> None:
        channel = DistributionChannel(kind=DistributionChannelKind.BLOG)

        assert channel.kind is DistributionChannelKind.BLOG
        assert channel.enabled is True

    def test_publishing_schedule_is_scheduled_flag(self) -> None:
        when = datetime(2026, 7, 1, tzinfo=UTC)
        scheduled = PublishingSchedule(scheduled_at=when)
        unscheduled = PublishingSchedule()

        assert scheduled.is_scheduled is True
        assert scheduled.requires_manual_release is True
        assert unscheduled.is_scheduled is False


class TestBootstrapWiring:
    """Scenario: bootstrap wires the module via manual DI (no global container)."""

    def test_bootstrap_returns_module_with_service(self) -> None:
        adapters = PublishingAdapters(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            unit_of_work=AsyncMock(),
        )

        module = bootstrap_module(platform=MagicMock(), adapters=adapters)

        assert isinstance(module, PublishingModule)
        assert isinstance(module.service, PublishingService)
        assert module.unit_of_work is adapters.unit_of_work


@pytest.mark.asyncio
async def test_bootstrapped_service_get_publication_uses_repo() -> None:
    """The wired service delegates to the injected carousel repository."""
    repo = AsyncMock(spec=CarouselRepository)
    project = CarouselProject(topic="AI", audience="devs", niche="tech")
    repo.get_project_by_id.return_value = project
    adapters = PublishingAdapters(
        carousel_repository=repo,
        unit_of_work=AsyncMock(),
    )

    module = bootstrap_module(platform=MagicMock(), adapters=adapters)
    result = await module.service.get_publication(project.id)

    repo.get_project_by_id.assert_awaited_once_with(project.id)
    assert result is not None
    assert result.project is project


@pytest.mark.asyncio
async def test_bootstrapped_service_get_publication_returns_none_when_absent() -> None:
    """The service returns None when the repository has no such project."""
    repo = AsyncMock(spec=CarouselRepository)
    repo.get_project_by_id.return_value = None
    adapters = PublishingAdapters(
        carousel_repository=repo,
        unit_of_work=AsyncMock(),
    )

    module = bootstrap_module(platform=MagicMock(), adapters=adapters)
    result = await module.service.get_publication(uuid4())

    assert result is None
