"""Unit tests for the completed-project slide-edit route handler (AE-0314).

Feature: Edit carousel text without regenerating images
  (see tests/features/carousel_text_edit_no_regen.feature)

Exercises the thin HTTP adapter directly: auth is delegated to
``get_carousel_project_for_workflow_user`` (patched), the service to a stub. Pins
the completed-only guard, the sanitize-on-the-wire boundary (AE-0289), and typed
409 conflict propagation.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.routes.carousels.deps import CarouselSlideEditRouteDeps
from rag_backend.api.routes.carousels.slide_edit import edit_carousel_slides
from rag_backend.api.schemas.carousel_slide_edit import CarouselSlideEditRequest
from rag_backend.api.schemas.carousel_workflow import LocalizedSlideReview
from rag_backend.application.services.carousel.carousel_slide_edit_service import (
    SlideEditCommand,
    SlideEditResult,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)
from rag_backend.domain.constants.carousel_slide_edit import (
    ERR_SLIDE_EDIT_NOT_COMPLETED,
    SLIDE_EDIT_STATUS_UPDATED,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)

_ACCESS_TARGET = (
    "rag_backend.api.routes.carousels.slide_edit.get_carousel_project_for_workflow_user"
)


def _project_model(*, status: str) -> MagicMock:
    model = MagicMock()
    model.status = status
    model.phase_status = "approved"
    model.lock_version = 1
    model.presentation_policy_version = None
    return model


def _result() -> SlideEditResult:
    return SlideEditResult(
        status=SLIDE_EDIT_STATUS_UPDATED,
        report={
            "validation_status": "valid",
            "validated_at": "2026-07-10T00:00:00Z",
            "blocking": False,
            "violations": [],
        },
        updated_slides=(1,),
        needs_republish=True,
        checkpoint_updated=True,
    )


def _deps(service: MagicMock) -> CarouselSlideEditRouteDeps:
    return CarouselSlideEditRouteDeps(
        current_user=_user(), db=cast(AsyncSession, MagicMock()), service=service
    )


def _payload(heading: str = "Corrected Heading") -> CarouselSlideEditRequest:
    return CarouselSlideEditRequest(
        edited_slides=[
            LocalizedSlideReview(
                slide_index=1,
                slide_type="content",
                presentation_pt={"heading": heading, "body": "Corpo limpo."},
                presentation_en={"heading": heading, "body": "Clean body."},
            )
        ]
    )


def _user() -> MagicMock:
    user = MagicMock()
    user.id = "user-1"
    return user


@pytest.mark.asyncio
@pytest.mark.unit
class TestSlideEditRoute:
    async def test_rejects_non_completed_project(self) -> None:
        model = _project_model(status=CarouselStatus.GENERATING_IMAGES.value)
        service = MagicMock()
        with (
            patch(_ACCESS_TARGET, AsyncMock(return_value=model)),
            pytest.raises(HTTPException) as exc,
        ):
            await edit_carousel_slides(uuid4(), _payload(), _deps(service))
        assert exc.value.status_code == 422
        assert exc.value.detail == ERR_SLIDE_EDIT_NOT_COMPLETED

    async def test_successful_edit_returns_fresh_report(self) -> None:
        model = _project_model(status=CarouselStatus.COMPLETED.value)
        service = MagicMock()
        service.edit = AsyncMock(return_value=_result())
        with patch(_ACCESS_TARGET, AsyncMock(return_value=model)):
            response = await edit_carousel_slides(uuid4(), _payload(), _deps(service))
        assert response.status == SLIDE_EDIT_STATUS_UPDATED
        assert response.needs_republish is True
        assert response.validation.blocking is False
        assert response.updated_slides == [1]

    async def test_sanitizes_edited_copy_on_the_wire(self) -> None:
        # AE-0289 boundary: markup is stripped before it reaches the service.
        model = _project_model(status=CarouselStatus.COMPLETED.value)
        service = MagicMock()
        service.edit = AsyncMock(return_value=_result())
        with patch(_ACCESS_TARGET, AsyncMock(return_value=model)):
            await edit_carousel_slides(
                uuid4(),
                _payload(heading="<img onerror=alert(1)>Keep Case"),
                _deps(service),
            )
        command = cast(SlideEditCommand, service.edit.call_args[0][0])
        sanitized_pt = command.edited_slides[0]["presentation_pt"]
        heading = cast(str, cast(dict[str, object], sanitized_pt)["heading"])
        assert "<" not in heading and ">" not in heading
        # Case is preserved (sanitize_display_input, not lowercasing).
        assert "Keep Case" in heading

    async def test_typed_conflict_propagates(self) -> None:
        model = _project_model(status=CarouselStatus.COMPLETED.value)
        service = MagicMock()
        service.edit = AsyncMock(
            side_effect=CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
            )
        )
        with (
            patch(_ACCESS_TARGET, AsyncMock(return_value=model)),
            pytest.raises(CarouselConflictError) as exc,
        ):
            await edit_carousel_slides(uuid4(), _payload(), _deps(service))
        assert exc.value.conflict.code == CONFLICT_CODE_MUTATION_IN_PROGRESS
