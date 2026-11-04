"""The Retry route's HTTP mapping and the rejected-approve refusal, without a DB.

Feature: tests/features/carousel_owner_retry_ae0606.feature
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.routes.carousel_retry import _capability, _response
from rag_backend.api.routes.carousels.editorial_workflow_routes_validate import (
    ensure_rendered_before_approve,
)
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.modules.generation_queue.retry_public import (
    RetryCapability,
    RetryKind,
    RetryRefusal,
    RetryResult,
)


def _body(response: JSONResponse) -> dict[str, object]:
    return json.loads(bytes(response.body))


@pytest.mark.unit
class TestRetryResponse:
    def test_an_accepted_retry_is_202_with_the_new_state(self) -> None:
        run_id = uuid4()
        response = _response(
            RetryResult(
                accepted=True,
                kind=RetryKind.REVISE,
                phase="content",
                phase_status="in_progress",
                lock_version=6,
                autopilot_run_id=run_id,
            )
        )
        assert response.status_code == 202
        assert _body(response) == {
            "accepted": True,
            "retry_kind": "revise",
            "current_phase": "content",
            "phase_status": "in_progress",
            "lock_version": 6,
            "autopilot_run_id": str(run_id),
        }

    def test_an_accepted_retry_without_a_run_has_no_run_id(self) -> None:
        response = _response(RetryResult(accepted=True, kind=RetryKind.REOPEN))
        assert _body(response)["autopilot_run_id"] is None

    # Scenario: A tap from someone who does not own the carousel changes nothing
    @pytest.mark.parametrize(
        ("refusal", "status"),
        [
            (RetryRefusal.NOT_FOUND, 404),
            (RetryRefusal.NOT_OWNER, 403),
            (RetryRefusal.NOT_ASSIGNED_REVIEWER, 403),
            (RetryRefusal.USE_REPROCESS, 409),
            (RetryRefusal.VERSION_CONFLICT, 409),
        ],
    )
    def test_a_refusal_maps_to_its_status(
        self, refusal: RetryRefusal, status: int
    ) -> None:
        response = _response(RetryResult(accepted=False, refusal=refusal))
        assert response.status_code == status
        assert _body(response) == {"detail": refusal.value}

    def test_a_result_without_kind_or_refusal_is_a_conflict(self) -> None:
        response = _response(RetryResult(accepted=False))
        assert response.status_code == 409
        assert _body(response) == {"detail": "concurrent_update"}

    # Scenario: The retry capability is read without any change
    def test_the_capability_maps_kind_and_refusal(self) -> None:
        accepted = _capability(
            RetryCapability(can_retry=True, kind=RetryKind.REDRIVE, lock_version=3)
        )
        refused = _capability(
            RetryCapability(can_retry=False, refusal=RetryRefusal.NO_CHECKPOINT)
        )
        assert (accepted.retry_kind, accepted.refusal_code) == ("redrive", None)
        assert accepted.lock_version == 3
        assert (refused.retry_kind, refused.refusal_code) == (None, "no_checkpoint")


@dataclass
class _Result:
    row: tuple[object, ...] | None

    def one_or_none(self) -> tuple[object, ...] | None:
        return self.row


@dataclass
class _Db:
    row: tuple[object, ...] | None

    async def execute(self, statement: object) -> _Result:
        del statement
        return _Result(self.row)


async def _check(row: tuple[object, ...] | None, expected: int = 5) -> None:
    await ensure_rendered_before_approve(cast(AsyncSession, _Db(row)), "p", expected)


@pytest.mark.unit
class TestApproveOnRejected:
    # Scenario: A website approve on a rejected carousel is refused
    async def test_an_approve_at_the_rejected_version_is_refused(self) -> None:
        with pytest.raises(CarouselConflictError) as exc:
            await _check((None, "research", "rejected", 5))
        assert exc.value.conflict.code == "carousel_rejected"

    async def test_a_stale_approve_is_left_to_the_lock_cas(self) -> None:
        await _check((None, "research", "rejected", 6))

    async def test_a_missing_carousel_passes(self) -> None:
        await _check(None)

    async def test_a_waiting_carousel_passes(self) -> None:
        await _check((None, "research", "awaiting_human", 5))

    async def test_a_pending_final_review_render_is_still_refused(self) -> None:
        with pytest.raises(CarouselConflictError) as exc:
            await _check((datetime.now(UTC), "final_review", "awaiting_human", 5))
        assert exc.value.conflict.code == "build_in_progress"
