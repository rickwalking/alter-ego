"""Exact-behaviour tests for the preview routes' project + access loaders.

Feature: Carousel i18n Blog and Design Token Endpoints
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_CAROUSEL_NOT_GENERATED,
)
from rag_backend.api.routes.carousels.preview import (
    PreviewAccessContext,
    _load_accessible_project,
    _load_accessible_project_with_output,
)
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.models.user import UserRole

_NOT_FOUND = 404
_FORBIDDEN = 403
_OUTPUT_DIR = "/tmp/carousel-out"

Loader = Callable[[PreviewAccessContext], Awaitable[CarouselProject]]
_LOADERS: list[Loader] = [
    _load_accessible_project,
    _load_accessible_project_with_output,
]


def _user() -> User:
    return User(
        id=uuid4(),
        email="viewer@example.com",
        full_name="Viewer",
        role=UserRole.EDITOR,
        hashed_password="hash",
    )


def _project(owner_id: str | None) -> CarouselProject:
    return CarouselProject(
        topic="T",
        audience="A",
        niche="N",
        output_dir=_OUTPUT_DIR,
        owner_id=owner_id,
    )


def _ctx(
    project: CarouselProject | None,
    user: User,
    reviewer_id: str | None = None,
) -> tuple[PreviewAccessContext, UUID]:
    project_id = uuid4()
    lookup = {project_id: project}
    reviewers = {project_id: reviewer_id}
    handlers = MagicMock()
    handlers.get_project = AsyncMock(side_effect=lookup.get)
    handlers.get_assigned_reviewer_id = AsyncMock(side_effect=reviewers.get)
    return PreviewAccessContext(project_id=project_id, user=user, handlers=handlers), (
        project_id
    )


@pytest.mark.unit
@pytest.mark.parametrize("loader", _LOADERS)
class TestPreviewLoaders:
    """Scenario: preview loaders enforce existence and owner/reviewer access."""

    async def test_missing_project_is_exact_404(self, loader: Loader) -> None:
        ctx, _ = _ctx(None, _user())
        with pytest.raises(HTTPException) as exc_info:
            await loader(ctx)
        assert exc_info.value.status_code == _NOT_FOUND
        assert exc_info.value.detail == ERR_CAROUSEL_NOT_FOUND

    async def test_owner_gets_project_loaded_by_id(self, loader: Loader) -> None:
        user = _user()
        project = _project(owner_id=str(user.id))
        ctx, project_id = _ctx(project, user)
        assert await loader(ctx) is project
        ctx.handlers.get_project.assert_awaited_once_with(project_id)

    async def test_assigned_reviewer_is_allowed(self, loader: Loader) -> None:
        user = _user()
        project = _project(owner_id=str(uuid4()))
        ctx, project_id = _ctx(project, user, reviewer_id=str(user.id))
        assert await loader(ctx) is project
        ctx.handlers.get_assigned_reviewer_id.assert_awaited_once_with(project_id)

    async def test_stranger_is_forbidden(self, loader: Loader) -> None:
        project = _project(owner_id=str(uuid4()))
        ctx, _ = _ctx(project, _user(), reviewer_id=str(uuid4()))
        with pytest.raises(HTTPException) as exc_info:
            await loader(ctx)
        assert exc_info.value.status_code == _FORBIDDEN


@pytest.mark.unit
class TestPreviewLoaderWithOutput:
    """Scenario: image preview requires a generated carousel output dir."""

    async def test_missing_output_dir_is_exact_404(self) -> None:
        user = _user()
        project = _project(owner_id=str(user.id))
        project.output_dir = None
        ctx, _ = _ctx(project, user)
        with pytest.raises(HTTPException) as exc_info:
            await _load_accessible_project_with_output(ctx)
        assert exc_info.value.status_code == _NOT_FOUND
        assert exc_info.value.detail == ERR_CAROUSEL_NOT_GENERATED
