"""Unit tests for the typed carousel conflict handler (AE-0316).

Gherkin: tests/features/carousel_typed_conflicts.feature
"""

import json
from datetime import UTC, datetime

import pytest
from fastapi import Request

from rag_backend.api.middleware.carousel_conflict_handler import (
    carousel_conflict_handler,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CAROUSEL_CONFLICT_CODES,
    CONFLICT_CODE_REVISION_CAP_EXCEEDED,
    CONFLICT_CODE_RUN_IN_PROGRESS,
    CONFLICT_MESSAGES,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)

RUN_STARTED_AT = datetime(2026, 7, 10, 3, 56, 37, tzinfo=UTC)
PHASE_CONTENT = "content"


def _request() -> Request:
    return Request(scope={"type": "http", "method": "POST", "path": "/x"})


def _body(response: object) -> dict[str, object]:
    rendered = getattr(response, "body", b"{}")
    return dict(json.loads(bytes(rendered)))


class TestCarouselConflictHandler:
    """Scenario: 409 body is additive — legacy detail string + conflict."""

    def test_detail_keeps_legacy_string_and_adds_conflict(self) -> None:
        error = CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
        )
        response = carousel_conflict_handler(_request(), error)
        assert response.status_code == 409
        body = _body(response)
        assert body["detail"] == CONFLICT_CODE_RUN_IN_PROGRESS
        conflict = body["conflict"]
        assert isinstance(conflict, dict)
        assert conflict["code"] == CONFLICT_CODE_RUN_IN_PROGRESS
        assert conflict["message"] == CONFLICT_MESSAGES[CONFLICT_CODE_RUN_IN_PROGRESS]

    def test_run_started_at_and_phase_serialize(self) -> None:
        error = CarouselConflictError(
            CarouselConflict.for_code(
                CONFLICT_CODE_REVISION_CAP_EXCEEDED,
                run_started_at=RUN_STARTED_AT,
                phase=PHASE_CONTENT,
            )
        )
        response = carousel_conflict_handler(_request(), error)
        body = _body(response)
        conflict = body["conflict"]
        assert isinstance(conflict, dict)
        assert conflict["phase"] == PHASE_CONTENT
        assert str(conflict["run_started_at"]).startswith("2026-07-10T03:56:37")

    @pytest.mark.parametrize("code", CAROUSEL_CONFLICT_CODES)
    def test_each_conflict_code_round_trips(self, code: str) -> None:
        """Rule-fires: every seeded conflict cause asserts its exact code."""
        error = CarouselConflictError(CarouselConflict.for_code(code))
        response = carousel_conflict_handler(_request(), error)
        body = _body(response)
        assert body["detail"] == code
        conflict = body["conflict"]
        assert isinstance(conflict, dict)
        assert conflict["code"] == code

    def test_non_conflict_exception_is_reraised(self) -> None:
        with pytest.raises(RuntimeError):
            carousel_conflict_handler(_request(), RuntimeError("boom"))
