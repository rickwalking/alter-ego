"""Async resume integration tests (RW-010-RW-013).

Feature: carousel_pipeline_consolidation.feature @cp-async-resume
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from rag_backend.application.services.carousel.editorial_workflow_support import (
    SSE_EVENT_ERROR,
    SSE_EVENT_REVIEW_REQUIRED,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_RESUME_ALREADY_IN_PROGRESS,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.models import UserRole
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    collect_hub_events_during,
    create_carousel,
    create_user,
    drain_background_tasks,
    get_lock_version,
    seed_workflow_phase,
    wait_for_workflow_state,
)


class TestAsyncEditorialResume:
    """Scenarios: async resume returns 202 and completes in background."""

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.phase_artifact_runner.generate_outline",
        new_callable=AsyncMock,
    )
    async def test_approve_research_returns_202_within_two_seconds(
        self,
        mock_outline: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Scenario: Approve research returns 202 within 2 seconds."""
        mock_outline.return_value = [
            {"slide_index": 1, "title": "Intro", "key_points": ["Hook"]},
        ]
        editor = await create_user("async-approve@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "research_findings": [{"title": "Finding", "summary": "Detail"}],
            },
        )
        version = await get_lock_version(project_id)

        started = time.monotonic()
        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": version},
            headers=auth_header(editor),
        )
        elapsed = time.monotonic() - started

        assert response.status_code == 202
        assert elapsed < 2.0
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["phase_status"] == PHASE_STATUS_IN_PROGRESS

        await drain_background_tasks()
        state = await wait_for_workflow_state(
            client,
            project_id,
            auth_header(editor),
            phase=PHASE_OUTLINE,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )
        assert state["outline"]

    @pytest.mark.asyncio
    async def test_resume_while_in_progress_returns_409(
        self,
        client: AsyncClient,
    ) -> None:
        """Scenario: Resume while phase_status is in_progress returns 409."""
        editor = await create_user("async-in-progress@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_OUTLINE,
            phase_status=PHASE_STATUS_IN_PROGRESS,
            extra_state={"outline": [{"title": "Intro"}]},
        )
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": version},
            headers=auth_header(editor),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == ERR_RESUME_ALREADY_IN_PROGRESS

    @pytest.mark.asyncio
    async def test_duplicate_approve_while_in_progress_returns_409(
        self,
        client: AsyncClient,
    ) -> None:
        """Scenario: Duplicate approve with same expected_version is idempotent."""
        editor = await create_user("async-duplicate@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "research_findings": [{"title": "Finding", "summary": "Detail"}],
            },
        )
        version = await get_lock_version(project_id)

        first, second = await asyncio.gather(
            client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": version},
                headers=auth_header(editor),
            ),
            client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": version},
                headers=auth_header(editor),
            ),
        )

        statuses = sorted([first.status_code, second.status_code])
        assert statuses[0] == 202
        assert statuses[1] == 409

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.phase_artifact_runner.generate_outline",
        new_callable=AsyncMock,
    )
    async def test_background_resume_publishes_review_required_for_outline_gate(
        self,
        mock_outline: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Scenario: Background resume publishes review_required when outline gate opens."""
        mock_outline.return_value = [
            {"slide_index": 1, "title": "Intro", "key_points": ["Hook"]},
        ]
        editor = await create_user("async-review@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_RESEARCH,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "research_findings": [{"title": "Finding", "summary": "Detail"}],
            },
        )
        version = await get_lock_version(project_id)

        async def resume_and_drain() -> None:
            response = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": version},
                headers=auth_header(editor),
            )
            assert response.status_code == 202
            await drain_background_tasks()

        events = await collect_hub_events_during(
            project_id,
            resume_and_drain,
            # AE-0315 adds run.started/stage_changed/finished to the stream
            expected_count=9,
        )
        review_events = [
            event for event in events if event.get("event") == SSE_EVENT_REVIEW_REQUIRED
        ]
        assert review_events
        assert review_events[0].get("phase") == PHASE_OUTLINE
        gate_payload = review_events[0].get("gate_payload")
        assert isinstance(gate_payload, dict)
        assert gate_payload.get("outline")

    @pytest.mark.asyncio
    @patch(
        "rag_backend.application.services.carousel.editorial_workflow_service.EditorialWorkflowService.resume_workflow",
        new_callable=AsyncMock,
    )
    async def test_background_resume_failure_publishes_recoverable_error_event(
        self,
        mock_resume_workflow: AsyncMock,
        client: AsyncClient,
    ) -> None:
        """Scenario: Background resume failure publishes recoverable error event."""
        mock_resume_workflow.side_effect = RuntimeError("content generation failed")
        editor = await create_user("async-failure@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_OUTLINE,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "research_findings": [{"title": "Finding", "summary": "Detail"}],
                "outline": [{"slide_index": 1, "title": "Intro"}],
            },
        )
        version = await get_lock_version(project_id)

        async def resume_and_drain() -> None:
            response = await client.post(
                f"/api/carousels/{project_id}/workflow/resume",
                json={"action": "approve", "expected_version": version},
                headers=auth_header(editor),
            )
            assert response.status_code == 202
            await drain_background_tasks()

        events = await collect_hub_events_during(
            project_id,
            resume_and_drain,
            # AE-0315 adds run lifecycle events ahead of the error event
            expected_count=4,
        )
        error_events = [
            event for event in events if event.get("event") == SSE_EVENT_ERROR
        ]
        assert error_events
        assert error_events[0].get("recoverable") is True
        assert error_events[0].get("message") == ERR_BACKGROUND_RESUME_FAILED

        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        session_maker = get_session_maker()
        async with session_maker() as session:
            project = await session.get(CarouselProjectModel, project_id)
            assert project is not None
            assert project.phase_status == PHASE_STATUS_FAILED
