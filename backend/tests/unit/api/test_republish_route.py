"""Unit tests for the carousel republish route handler (AE-0313).

Feature: Republish a completed carousel's artifacts
  Scenario: Failed republish never corrupts a completed project
  Scenario: Concurrent republishes serialize on the build lock
  (see tests/features/carousel_republish.feature)

Exercises the thin HTTP adapter directly: auth is delegated to
``get_carousel_project_for_workflow_user`` (patched), the finalize pipeline to
``republish_completed_carousel`` (patched). Pins the completed <-> phase_status
invariant: a completed carousel with an in-progress run is refused.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.routes.carousels import republish as republish_route
from rag_backend.api.routes.carousels.republish import republish_carousel
from rag_backend.application.services.carousel.editorial_finalize import (
    CarouselFinalizeResult,
)
from rag_backend.domain.constants.artifact_build import ERR_ARTIFACT_BUILD_CONFLICT
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_BUILD_IN_PROGRESS,
    CONFLICT_CODE_RUN_IN_PROGRESS,
)
from rag_backend.domain.constants.carousel_republish import (
    ERR_REPUBLISH_NOT_COMPLETED,
    REPUBLISH_STATUS_REPUBLISHED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.models.carousel_conflict import CarouselConflictError

_ACCESS_TARGET = (
    "rag_backend.api.routes.carousels.republish.get_carousel_project_for_workflow_user"
)
_SERVICE_TARGET = (
    "rag_backend.api.routes.carousels.republish.republish_completed_carousel"
)


def _project_model(
    *,
    status: str,
    phase_status: str = PHASE_STATUS_APPROVED,
) -> MagicMock:
    model = MagicMock()
    model.status = status
    model.phase_status = phase_status
    model.artifact_version = "sha256-" + "a" * 64
    model.pdf_path = "/out/pt/carousel.pdf"
    model.pdf_path_en = "/out/en/carousel.pdf"
    return model


def _db(refreshed: MagicMock | None) -> AsyncSession:
    db = MagicMock()
    db.get = AsyncMock(return_value=refreshed)
    return cast(AsyncSession, db)


@pytest.mark.asyncio
@pytest.mark.unit
class TestRepublishRoute:
    async def test_rejects_non_completed_project(self) -> None:
        model = _project_model(status=CarouselStatus.GENERATING_IMAGES.value)
        with (
            patch(_ACCESS_TARGET, AsyncMock(return_value=model)),
            pytest.raises(HTTPException) as exc_info,
        ):
            await republish_carousel(uuid4(), _db(None), MagicMock())
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == ERR_REPUBLISH_NOT_COMPLETED

    async def test_rejects_active_run_on_completed_project(self) -> None:
        """completed <-> phase_status invariant: an in-progress run blocks it."""
        model = _project_model(
            status=CarouselStatus.COMPLETED.value,
            phase_status=PHASE_STATUS_IN_PROGRESS,
        )
        with (
            patch(_ACCESS_TARGET, AsyncMock(return_value=model)),
            pytest.raises(CarouselConflictError) as exc_info,
        ):
            await republish_carousel(uuid4(), _db(None), MagicMock())
        assert exc_info.value.conflict.code == CONFLICT_CODE_RUN_IN_PROGRESS

    async def test_successful_republish_returns_new_version(self) -> None:
        # The finalize pipeline refreshes the same session-identity project row;
        # the route reads the new version straight off it (no ORM re-fetch).
        model = _project_model(status=CarouselStatus.COMPLETED.value)
        model.artifact_version = "sha256-" + "f" * 64
        with (
            patch(_ACCESS_TARGET, AsyncMock(return_value=model)),
            patch(
                _SERVICE_TARGET,
                AsyncMock(
                    return_value=CarouselFinalizeResult(completed=True, errors=())
                ),
            ),
        ):
            response = await republish_carousel(uuid4(), _db(None), MagicMock())
        assert response.status == REPUBLISH_STATUS_REPUBLISHED
        assert response.artifact_version == "sha256-" + "f" * 64
        assert response.pdf_path == "/out/pt/carousel.pdf"

    async def test_build_conflict_maps_to_typed_409(self) -> None:
        model = _project_model(status=CarouselStatus.COMPLETED.value)
        with (
            patch(_ACCESS_TARGET, AsyncMock(return_value=model)),
            patch(
                _SERVICE_TARGET,
                AsyncMock(
                    return_value=CarouselFinalizeResult(
                        completed=False, errors=(ERR_ARTIFACT_BUILD_CONFLICT,)
                    )
                ),
            ),
            pytest.raises(CarouselConflictError) as exc_info,
        ):
            await republish_carousel(uuid4(), _db(None), MagicMock())
        assert exc_info.value.conflict.code == CONFLICT_CODE_BUILD_IN_PROGRESS

    async def test_health_failure_maps_to_422(self) -> None:
        model = _project_model(status=CarouselStatus.COMPLETED.value)
        with (
            patch(_ACCESS_TARGET, AsyncMock(return_value=model)),
            patch(
                _SERVICE_TARGET,
                AsyncMock(
                    return_value=CarouselFinalizeResult(
                        completed=False, errors=("pt PDF missing",)
                    )
                ),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await republish_carousel(uuid4(), _db(None), MagicMock())
        assert exc_info.value.status_code == 422
        assert "pt PDF missing" in exc_info.value.detail


@pytest.mark.unit
def test_route_module_exports_router() -> None:
    assert republish_route.router is not None
