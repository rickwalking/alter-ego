"""Unit tests for the presentation module skeleton + shims (AE-0117).

These tests prove the behavior-preserving scaffolding:

* the carousel repository port and the carousel entities are **object-identity
  shims** (re-exports of the canonical objects);
* the presentation policy types and the per-slide presentation/validation models
  are re-exported as IDENTICAL objects (no new domain strings);
* the facade exposes the documented public API;
* ``bootstrap_module`` wires the module via manual constructor injection (no
  global container);
* ``PresentationProject`` / ``DesignPolicy`` / ``SlideView`` are importable,
  typed, and constructible.

Behavior-preserving scaffolding; verified by mypy/lint-imports + this safety net
(see ticket AE-0117 — Gherkin not applicable).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.modules.presentation import (
    CarouselProject,
    CarouselRepository,
    CarouselSlide,
    DesignPolicy,
    PresentationAdapters,
    PresentationModule,
    PresentationProject,
    PresentationService,
    SlideView,
    bootstrap_module,
)


class TestRepositoryPortShimIdentity:
    """Scenario: The carousel repository port re-exports to the same object."""

    def test_carousel_repository_is_identical_object(self) -> None:
        from rag_backend.domain.protocols.repositories import (
            CarouselRepository as Canonical,
        )
        from rag_backend.modules.presentation.domain.ports import (
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
        from rag_backend.modules.presentation.domain.models import (
            CarouselProject as ModuleProject,
        )
        from rag_backend.modules.presentation.domain.models import (
            CarouselSlide as ModuleSlide,
        )

        assert ModuleProject is CanonicalProject
        assert ModuleSlide is CanonicalSlide


class TestPolicyTypeShimIdentity:
    """Scenario: Presentation policy types re-export to identical objects."""

    def test_policy_types_are_identical_objects(self) -> None:
        from rag_backend.application.services.carousel.presentation_policy_types import (
            CarouselPresentationPolicy as CanonicalPolicy,
        )
        from rag_backend.application.services.carousel.presentation_policy_types import (
            SlideTypePolicy as CanonicalSlideTypePolicy,
        )
        from rag_backend.modules.presentation.domain.models import (
            CarouselPresentationPolicy as ModulePolicy,
        )
        from rag_backend.modules.presentation.domain.models import (
            SlideTypePolicy as ModuleSlideTypePolicy,
        )

        assert ModulePolicy is CanonicalPolicy
        assert ModuleSlideTypePolicy is CanonicalSlideTypePolicy

    def test_facade_policy_type_is_identical_object(self) -> None:
        from rag_backend.application.services.carousel.presentation_policy_types import (
            CarouselPresentationPolicy as Canonical,
        )
        from rag_backend.modules.presentation import (
            CarouselPresentationPolicy as Facade,
        )

        assert Facade is Canonical


class TestSlideModelShimIdentity:
    """Scenario: Slide presentation/validation models re-export identically."""

    def test_slide_models_are_identical_objects(self) -> None:
        from rag_backend.domain.models.carousel_presentation import (
            ContentSlideCopy as CanonicalContent,
        )
        from rag_backend.domain.models.carousel_presentation import (
            SlideValidationViolation as CanonicalViolation,
        )
        from rag_backend.modules.presentation.domain.models import (
            ContentSlideCopy as ModuleContent,
        )
        from rag_backend.modules.presentation.domain.models import (
            SlideValidationViolation as ModuleViolation,
        )

        assert ModuleContent is CanonicalContent
        assert ModuleViolation is CanonicalViolation


class TestFacadeSurface:
    """Scenario: The facade exposes the documented public API."""

    def test_public_symbols_exported(self) -> None:
        from rag_backend.modules import presentation as facade

        for name in (
            "PresentationService",
            "PresentationProject",
            "DesignPolicy",
            "SlideView",
            "PresentationAdapters",
            "PresentationModule",
            "CarouselRepository",
            "CarouselProject",
            "CarouselSlide",
            "CarouselPresentationPolicy",
            "SlideTypePolicy",
            "ContentSlideCopy",
            "SlideValidationReport",
            "SlideValidationViolation",
            "PresentationPolicyPort",
            "SlideValidationPort",
            "bootstrap_module",
        ):
            assert name in facade.__all__
            assert hasattr(facade, name)


class TestDomainEntities:
    """Scenario: PresentationProject/DesignPolicy/SlideView are typed + usable."""

    def test_presentation_project_views_carousel_fields(self) -> None:
        project = CarouselProject(topic="AI", audience="devs", niche="tech")
        project.artifact_version = "art-7"
        presentation = PresentationProject(project=project)

        assert presentation.project is project
        assert presentation.project_id == project.id
        assert presentation.artifact_version == "art-7"
        assert isinstance(presentation.design_policy, DesignPolicy)
        assert presentation.design_policy.template_version == project.template_version

    def test_slide_view_from_slide(self) -> None:
        slide = CarouselSlide(
            project_id=CarouselProject(
                topic="AI",
                audience="devs",
                niche="tech",
            ).id,
            slide_number=1,
            slide_type="intro",
            heading="Hi",
            body="Body",
            html_content="<div/>",
            image_path="/img/1.png",
        )

        view = SlideView.from_slide(slide)

        assert isinstance(view, SlideView)
        assert view.slide_number == 1
        assert view.slide_type == "intro"
        assert view.html_content == "<div/>"
        assert view.image_path == "/img/1.png"


class TestBootstrapWiring:
    """Scenario: bootstrap wires the module via manual DI (no global container)."""

    def test_bootstrap_returns_module_with_service(self) -> None:
        adapters = PresentationAdapters(
            repository=AsyncMock(spec=CarouselRepository),
            unit_of_work=AsyncMock(),
        )

        module = bootstrap_module(platform=MagicMock(), adapters=adapters)

        assert isinstance(module, PresentationModule)
        assert isinstance(module.service, PresentationService)
        assert module.unit_of_work is adapters.unit_of_work


class TestServicePortGuards:
    """Scenario: use cases without their port wired raise a clear error."""

    @pytest.mark.asyncio
    async def test_load_policy_without_port_raises(self) -> None:
        service = PresentationService(repository=AsyncMock(spec=CarouselRepository))

        with pytest.raises(RuntimeError, match="presentation port not wired: policy"):
            await service.load_policy("v1")

    @pytest.mark.asyncio
    async def test_validate_slides_without_port_raises(self) -> None:
        service = PresentationService(repository=AsyncMock(spec=CarouselRepository))

        with pytest.raises(
            RuntimeError,
            match="presentation port not wired: slide_validation",
        ):
            await service.validate_slides("proj-1")
