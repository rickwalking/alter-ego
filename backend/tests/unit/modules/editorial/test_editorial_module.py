"""Unit tests for the editorial module skeleton + shims (AE-0108).

These tests prove the behavior-preserving scaffolding:

* the carousel repository port and the carousel entities are **object-identity
  shims** (re-exports of the canonical objects);
* the workflow status language is re-exported from the canonical
  ``rag_backend.domain.constants.carousel_workflow`` (no new strings,
  object-identical);
* the facade exposes the documented public API;
* ``bootstrap_module`` wires the module via manual constructor injection (no
  global container);
* ``EditorialProject`` / ``EditorialWorkflow`` are importable and typed.

Behavior-preserving scaffolding; verified by mypy/lint-imports + this safety net
(see ticket AE-0108 — Gherkin not applicable).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.modules.editorial import (
    CarouselProject,
    CarouselRepository,
    CarouselStatus,
    EditorialAdapters,
    EditorialModule,
    EditorialProject,
    EditorialService,
    EditorialWorkflow,
    bootstrap_module,
)


class TestRepositoryPortShimIdentity:
    """Scenario: The carousel repository port re-exports to the same object."""

    def test_carousel_repository_is_identical_object(self) -> None:
        from rag_backend.domain.protocols.repositories import (
            CarouselRepository as Canonical,
        )
        from rag_backend.modules.editorial.domain.ports import (
            CarouselRepository as ModulePort,
        )

        assert Canonical is ModulePort


class TestEntityShimIdentity:
    """Scenario: Carousel entities re-export to identical class objects."""

    def test_carousel_entities_are_identical_classes(self) -> None:
        from rag_backend.domain.models import (
            CarouselProject as CanonicalProject,
        )
        from rag_backend.domain.models import (
            CarouselSlide as CanonicalSlide,
        )
        from rag_backend.domain.models import (
            CarouselStatus as CanonicalStatus,
        )
        from rag_backend.modules.editorial.domain.models import (
            CarouselProject as ModuleProject,
        )
        from rag_backend.modules.editorial.domain.models import (
            CarouselSlide as ModuleSlide,
        )
        from rag_backend.modules.editorial.domain.models import (
            CarouselStatus as ModuleStatus,
        )

        assert ModuleProject is CanonicalProject
        assert ModuleSlide is CanonicalSlide
        assert ModuleStatus is CanonicalStatus


class TestStatusConstantShimIdentity:
    """Scenario: Workflow status constants re-export to identical objects."""

    def test_phase_constants_are_identical_objects(self) -> None:
        from rag_backend.domain.constants.carousel_workflow import (
            CAROUSEL_WORKFLOW_PHASES as CANONICAL_PHASES,
        )
        from rag_backend.domain.constants.carousel_workflow import (
            PHASE_RESEARCH as CANONICAL_RESEARCH,
        )
        from rag_backend.domain.constants.carousel_workflow import (
            REVIEW_ACTIONS as CANONICAL_ACTIONS,
        )
        from rag_backend.modules.editorial.domain.status import (
            CAROUSEL_WORKFLOW_PHASES as MODULE_PHASES,
        )
        from rag_backend.modules.editorial.domain.status import (
            PHASE_RESEARCH as MODULE_RESEARCH,
        )
        from rag_backend.modules.editorial.domain.status import (
            REVIEW_ACTIONS as MODULE_ACTIONS,
        )

        assert MODULE_RESEARCH is CANONICAL_RESEARCH
        assert MODULE_PHASES is CANONICAL_PHASES
        assert MODULE_ACTIONS is CANONICAL_ACTIONS

    def test_facade_status_constant_is_identical_object(self) -> None:
        from rag_backend.domain.constants.carousel_workflow import (
            PHASE_RESEARCH as CANONICAL_PHASE_RESEARCH,
        )
        from rag_backend.modules.editorial import (
            PHASE_RESEARCH as FACADE_PHASE_RESEARCH,
        )

        assert FACADE_PHASE_RESEARCH is CANONICAL_PHASE_RESEARCH


class TestFacadeSurface:
    """Scenario: The facade exposes the documented public API."""

    def test_public_symbols_exported(self) -> None:
        from rag_backend.modules import editorial as facade

        for name in (
            "EditorialService",
            "EditorialProject",
            "EditorialWorkflow",
            "EditorialAdapters",
            "EditorialModule",
            "CarouselRepository",
            "CarouselProject",
            "CarouselStatus",
            "PHASE_RESEARCH",
            "REVIEW_ACTIONS",
            "bootstrap_module",
        ):
            assert name in facade.__all__
            assert hasattr(facade, name)


class TestDomainEntities:
    """Scenario: EditorialProject/EditorialWorkflow are typed and constructible."""

    def test_editorial_workflow_defaults(self) -> None:
        workflow = EditorialWorkflow()

        from rag_backend.domain.constants.carousel_workflow import (
            PHASE_BRIEF,
            PHASE_STATUS_PENDING,
        )

        assert workflow.phase == PHASE_BRIEF
        assert workflow.phase_status == PHASE_STATUS_PENDING
        assert workflow.revision_count == 0

    def test_editorial_project_wraps_carousel_project(self) -> None:
        project = CarouselProject(topic="AI", audience="devs", niche="tech")
        editorial = EditorialProject(project=project)

        assert editorial.project is project
        assert editorial.project_id == project.id
        assert isinstance(editorial.workflow, EditorialWorkflow)


class TestBootstrapWiring:
    """Scenario: bootstrap wires the module via manual DI (no global container)."""

    def test_bootstrap_returns_module_with_service(self) -> None:
        adapters = EditorialAdapters(
            repository=AsyncMock(spec=CarouselRepository),
            unit_of_work=AsyncMock(),
        )

        module = bootstrap_module(platform=MagicMock(), adapters=adapters)

        assert isinstance(module, EditorialModule)
        assert isinstance(module.service, EditorialService)
        assert module.unit_of_work is adapters.unit_of_work


@pytest.mark.asyncio
async def test_bootstrapped_service_get_project_uses_repo() -> None:
    """The wired service delegates to the injected carousel repository."""
    repo = AsyncMock(spec=CarouselRepository)
    project = CarouselProject(topic="AI", audience="devs", niche="tech")
    repo.get_project_by_id.return_value = project
    adapters = EditorialAdapters(repository=repo, unit_of_work=AsyncMock())

    module = bootstrap_module(platform=MagicMock(), adapters=adapters)
    result = await module.service.get_project(project.id)

    repo.get_project_by_id.assert_awaited_once_with(project.id)
    assert result is not None
    assert result.project is project


@pytest.mark.asyncio
async def test_bootstrapped_service_get_project_returns_none_when_absent() -> None:
    """The service returns None when the repository has no such project."""
    repo = AsyncMock(spec=CarouselRepository)
    repo.get_project_by_id.return_value = None
    adapters = EditorialAdapters(repository=repo, unit_of_work=AsyncMock())

    module = bootstrap_module(platform=MagicMock(), adapters=adapters)
    result = await module.service.get_project(uuid4())

    assert result is None


def test_carousel_status_facade_is_canonical() -> None:
    """The re-exported CarouselStatus enum is the canonical object."""
    from rag_backend.domain.models import CarouselStatus as Canonical

    assert CarouselStatus is Canonical
