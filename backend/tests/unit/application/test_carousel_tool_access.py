"""Unit tests for RAG carousel tool access checks."""

from __future__ import annotations

from uuid import uuid4

from rag_backend.application.tools.carousel.access import (
    CarouselToolAccessContext,
    verify_carousel_tool_access,
    verify_carousel_workflow_start_access,
)
from rag_backend.domain.constants.access_control import ERR_CAROUSEL_TOOL_ACCESS_DENIED
from rag_backend.domain.models import CarouselProject, CarouselTheme


def _project(*, owner_id: str | None = "owner-1") -> CarouselProject:
    return CarouselProject(
        topic="Topic",
        audience="Audience",
        niche="Niche",
        theme=CarouselTheme.AUTO,
        owner_id=owner_id,
    )


class TestCarouselToolAccess:
    """Scenario: RAG tools enforce conversation-scoped project ownership."""

    def test_allows_owner_on_bound_project(self) -> None:
        project = _project(owner_id="user-1")
        access = CarouselToolAccessContext(
            owner_user_id="user-1",
            bound_project_id=str(project.id),
        )

        assert verify_carousel_tool_access(project, access) is None

    def test_denies_other_owner(self) -> None:
        project = _project(owner_id="owner-1")
        access = CarouselToolAccessContext(
            owner_user_id="user-2",
            bound_project_id=str(project.id),
        )

        assert (
            verify_carousel_tool_access(project, access)
            == ERR_CAROUSEL_TOOL_ACCESS_DENIED
        )

    def test_denies_mismatched_bound_project(self) -> None:
        project = _project(owner_id="user-1")
        access = CarouselToolAccessContext(
            owner_user_id="user-1",
            bound_project_id=str(uuid4()),
        )

        assert (
            verify_carousel_tool_access(project, access)
            == ERR_CAROUSEL_TOOL_ACCESS_DENIED
        )

    def test_denies_orphan_project_without_owner(self) -> None:
        project = _project(owner_id=None)
        access = CarouselToolAccessContext(
            owner_user_id="user-1",
            bound_project_id=str(project.id),
        )

        assert (
            verify_carousel_tool_access(project, access)
            == ERR_CAROUSEL_TOOL_ACCESS_DENIED
        )

    def test_workflow_start_allows_owner_without_bound_match(self) -> None:
        project = _project(owner_id="user-1")
        access = CarouselToolAccessContext(
            owner_user_id="user-1",
            bound_project_id=str(uuid4()),
        )

        assert verify_carousel_workflow_start_access(project, access) is None

    def test_workflow_start_denies_other_owner(self) -> None:
        project = _project(owner_id="owner-1")
        access = CarouselToolAccessContext(owner_user_id="user-2")

        assert (
            verify_carousel_workflow_start_access(project, access)
            == ERR_CAROUSEL_TOOL_ACCESS_DENIED
        )

    def test_tool_access_without_bound_project_uses_workflow_start(self) -> None:
        project = _project(owner_id="user-1")
        access = CarouselToolAccessContext(
            owner_user_id="user-1", bound_project_id=None
        )

        assert verify_carousel_tool_access(project, access) is None

    def test_workflow_start_denies_orphan_project(self) -> None:
        project = _project(owner_id=None)
        access = CarouselToolAccessContext(owner_user_id="user-1")

        assert (
            verify_carousel_workflow_start_access(project, access)
            == ERR_CAROUSEL_TOOL_ACCESS_DENIED
        )
