"""Carousel access control and artifact health assertions."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException

from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.application.services.carousel.artifact_health import (
    CarouselArtifactHealthRequest,
    evaluate_carousel_artifacts,
    format_artifact_health_errors,
)
from rag_backend.domain.constants.access_control import ERR_CAROUSEL_NOT_PUBLIC
from rag_backend.domain.models import CarouselProject, CarouselSlide, User


def assert_carousel_public(project: CarouselProject) -> None:
    """Allow only published carousels on public media routes."""
    if project.is_public:
        return
    raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_PUBLIC)


def assert_carousel_project_access(
    project: CarouselProject,
    user: User,
    *,
    assigned_reviewer_id: str | None = None,
) -> None:
    """Allow project owners, admins, and assigned reviewers on preview routes."""
    if user.is_admin():
        return
    if assigned_reviewer_id and str(user.id) == assigned_reviewer_id:
        return
    assert_domain_owner_or_admin(project.owner_id, user)


def assert_carousel_public_or_editor(
    project: CarouselProject,
    user: User | None,
) -> None:
    """Deprecated: public routes must use assert_carousel_public only."""
    _ = user
    assert_carousel_public(project)


def assert_carousel_artifacts_healthy(
    project: CarouselProject,
    slides: Sequence[CarouselSlide],
) -> None:
    report = evaluate_carousel_artifacts(
        CarouselArtifactHealthRequest(project=project, slides=slides)
    )
    if report.ok:
        return
    raise HTTPException(
        status_code=409,
        detail=format_artifact_health_errors(report.errors),
    )
