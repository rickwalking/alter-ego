"""Carousel consolidation integration tests.

Feature: carousel_pipeline_consolidation.feature
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.carousel_workflow import (
    ERR_REVISE_FEEDBACK_REQUIRED,
    ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
    PHASE_CONTENT,
    PHASE_FINAL_REVIEW,
    PHASE_OUTLINE,
    PHASE_STATUS_AWAITING_HUMAN,
)
from rag_backend.domain.constants.persona import ERR_PERSONA_NOT_FOUND
from rag_backend.domain.constants.workflow_validation import ERR_NOT_ASSIGNED_REVIEWER
from rag_backend.domain.models import CarouselStatus, UserRole
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    drain_background_tasks,
    get_lock_version,
    seed_workflow_assigned_reviewer,
    seed_workflow_phase,
    wait_for_workflow_state,
)


class TestWorkflowOptimisticLock:
    """Scenario: Optimistic lock conflict on concurrent resume."""

    @pytest.mark.asyncio
    async def test_resume_rejects_stale_expected_version(
        self, client: AsyncClient
    ) -> None:
        editor = await create_user("lock@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)

        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        session_maker = get_session_maker()
        async with session_maker() as session:
            project = await session.get(CarouselProjectModel, project_id)
            assert project is not None
            project.lock_version = 3
            await session.commit()

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": 2},
            headers=auth_header(editor),
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "version_conflict"

        async with session_maker() as session:
            project = await session.get(CarouselProjectModel, project_id)
            assert project is not None
            assert project.lock_version == 3


class TestEditorialWorkflowValidation:
    """Scenarios: workflow API input validation and reviewer access control."""

    @pytest.mark.asyncio
    async def test_resume_rejects_non_assigned_reviewer(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Resume blocked for reviewer who is not assigned."""
        owner = await create_user("owner@example.com", UserRole.EDITOR)
        assigned = await create_user("assigned@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        await seed_workflow_assigned_reviewer(client, project_id, str(assigned.id))

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": 1},
            headers=auth_header(owner),
        )
        assert response.status_code == 403
        assert response.json()["detail"] == ERR_NOT_ASSIGNED_REVIEWER
        assert await get_lock_version(project_id) == 1

    @pytest.mark.asyncio
    async def test_assigned_reviewer_can_read_workflow_state(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Assigned reviewer can access editorial workflow state."""
        owner = await create_user("owner-state@example.com", UserRole.EDITOR)
        assigned = await create_user("assigned-state@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        await seed_workflow_assigned_reviewer(client, project_id, str(assigned.id))

        response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(assigned),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["current_phase"] == "research"

    @pytest.mark.asyncio
    async def test_assigned_reviewer_can_resume_workflow(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Assigned reviewer can resume editorial workflow."""
        owner = await create_user("owner-resume@example.com", UserRole.EDITOR)
        assigned = await create_user("assigned-resume@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        await seed_workflow_assigned_reviewer(client, project_id, str(assigned.id))

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "approve", "expected_version": 1},
            headers=auth_header(assigned),
        )
        assert response.status_code == 202
        await drain_background_tasks()
        payload = await wait_for_workflow_state(
            client,
            project_id,
            auth_header(assigned),
        )
        assert payload["current_phase"] in {"research", "outline"}

    @pytest.mark.asyncio
    async def test_resume_rejects_invalid_action(self, client: AsyncClient) -> None:
        """Scenario: Resume rejects unknown review actions at API boundary."""
        editor = await create_user("invalid-action@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "invalid_action", "expected_version": 1},
            headers=auth_header(editor),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["edit", "reject"])
    async def test_resume_rejects_unsupported_review_actions(
        self,
        client: AsyncClient,
        action: str,
    ) -> None:
        """Scenario: Resume rejects edit/reject until explicitly implemented."""
        from rag_backend.domain.constants.carousel_workflow import (
            ERR_UNSUPPORTED_REVIEW_ACTION,
        )

        editor = await create_user(f"{action}-action@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": action, "expected_version": 1},
            headers=auth_header(editor),
        )
        assert response.status_code == 422
        assert response.json()["detail"] == ERR_UNSUPPORTED_REVIEW_ACTION

    @pytest.mark.asyncio
    async def test_resume_rejects_empty_revise_feedback(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Revise action requires non-empty feedback text."""
        editor = await create_user("empty-feedback@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_OUTLINE,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={"action": "revise", "feedback": "   ", "expected_version": 1},
            headers=auth_header(editor),
        )
        assert response.status_code == 422
        assert response.json()["detail"] == ERR_REVISE_FEEDBACK_REQUIRED

    @pytest.mark.asyncio
    async def test_start_rejects_unknown_persona(self, client: AsyncClient) -> None:
        """Scenario: Start workflow rejects unknown persona_id."""
        editor = await create_user("persona@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/start",
            json={
                "topic": "Topic",
                "audience": "Audience",
                "brief": "Brief",
                "persona_id": "00000000-0000-0000-0000-000000000099",
            },
            headers=auth_header(editor),
        )
        assert response.status_code == 404
        assert response.json()["detail"] == ERR_PERSONA_NOT_FOUND


class TestWorkflowPhaseArtifacts:
    """Scenarios: phase artifacts and persona gate at human review."""

    @pytest.mark.asyncio
    async def test_content_gate_state_includes_persona_scores(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Content gate includes slide drafts and persona scores."""
        editor = await create_user("content-gate@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_CONTENT,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "persona_scores": {"default": {"overall": 65}},
                "slide_drafts": [{"draft_text": "Slide body"}],
            },
        )

        response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(editor),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["slide_drafts"]
        assert payload["persona_scores"]


class TestInstagramPublishGate:
    """Scenario: Instagram publish requires editorial approval."""

    @pytest.mark.asyncio
    async def test_instagram_publish_rejected_without_workflow_approval(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Instagram publish blocked when workflow is not approved."""
        from rag_backend.infrastructure.database.config import get_session_maker
        from rag_backend.infrastructure.database.models.carousel import (
            CarouselProjectModel,
        )

        editor = await create_user("ig-blocked@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        session_maker = get_session_maker()
        async with session_maker() as session:
            model = await session.get(CarouselProjectModel, project_id)
            assert model is not None
            model.status = CarouselStatus.COMPLETED.value
            await session.commit()

        response = await client.post(
            f"/api/carousels/{project_id}/publish/instagram",
            json={"caption": "Test caption"},
            headers=auth_header(editor),
        )
        assert response.status_code == 403
        assert response.json()["detail"] == ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH


class TestEditorialWorkflowReviseAndFailure:
    """Scenarios: feedback persistence, send-back routing, invalid JSON."""

    @pytest.mark.asyncio
    async def test_content_revise_persists_phase_feedback(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Stored feedback is passed to regeneration on revise."""
        editor = await create_user("feedback@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_CONTENT,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "slide_drafts": [{"draft_text": "Formal slide copy"}],
                "outline": [{"slide_index": 1, "title": "Intro", "key_points": []}],
            },
        )
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={
                "action": "revise",
                "feedback": "Slide 2 tone is too formal",
                "expected_version": version,
            },
            headers=auth_header(editor),
        )
        assert response.status_code == 202
        await drain_background_tasks()
        state_response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(editor),
        )
        assert state_response.status_code == 200
        state_payload = state_response.json()
        phase_feedback = state_payload.get("phase_feedback", {})
        assert isinstance(phase_feedback, dict)
        stored_feedback = [
            note
            for notes in phase_feedback.values()
            if isinstance(notes, list)
            for note in notes
        ]
        assert "slide 2 tone is too formal" in stored_feedback
        revision_counts = state_payload.get("revision_count", {})
        assert isinstance(revision_counts, dict)
        assert sum(revision_counts.values()) >= 1

    @pytest.mark.asyncio
    async def test_final_review_send_back_to_content(self, client: AsyncClient) -> None:
        """Scenario: Final review revise routes to selected earlier phase."""
        from rag_backend.agents.carousel_workflow_nodes import (
            review_updates_from_response,
        )
        from rag_backend.domain.constants.carousel_workflow import (
            REVIEW_ACTION_REVISE,
            SEND_BACK_TARGET_PHASE_KEY,
            STRUCTURED_FEEDBACK_KEY,
            STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
        )

        updates = review_updates_from_response({
            "action": REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY: {
                STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_CONTENT,
            },
        })

        assert updates[SEND_BACK_TARGET_PHASE_KEY] == PHASE_CONTENT
        assert updates["current_phase"] == PHASE_CONTENT

        editor = await create_user("sendback@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_FINAL_REVIEW,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={"rubric_scores": {"overall": 80}},
        )
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={
                "action": "revise",
                "feedback": "Rewrite intro",
                "expected_version": version,
                "structured_feedback": {"target_phase": PHASE_CONTENT},
            },
            headers=auth_header(editor),
        )
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_send_back_files_feedback_under_content_and_preserves_images(
        self, client: AsyncClient
    ) -> None:
        """AE-0288: a final-review send-back to content files the reviewer note
        under ``content`` (not ``final_review``) so the content node's
        regeneration notes pick it up, and leaves the generated images untouched.

        (Graph re-entry from an approved/END checkpoint is covered by the engine
        unit test; the seed harness keeps the real interrupt at research, so
        this asserts the API-layer feedback keying + image preservation.)
        """
        images = [f"/app/output/carousels/x/images/slide_{n}.jpg" for n in range(1, 7)]
        editor = await create_user("sendbackimg@example.com", UserRole.EDITOR)
        project_id = await create_carousel(editor, is_public=False)
        await seed_workflow_phase(
            client,
            project_id,
            phase=PHASE_FINAL_REVIEW,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
            extra_state={
                "rubric_scores": {"overall": 80},
                "outline": [{"slide_index": 1, "title": "Intro", "key_points": []}],
                "slide_drafts": [{"draft_text": "Repetitive copy"}],
                "image_assets": images,
            },
        )
        version = await get_lock_version(project_id)

        response = await client.post(
            f"/api/carousels/{project_id}/workflow/resume",
            json={
                "action": "revise",
                "feedback": "Slides repeat; diversify per the research",
                "expected_version": version,
                "structured_feedback": {"target_phase": PHASE_CONTENT},
            },
            headers=auth_header(editor),
        )
        assert response.status_code == 202
        await drain_background_tasks()
        state_response = await client.get(
            f"/api/carousels/{project_id}/workflow/state",
            headers=auth_header(editor),
        )
        assert state_response.status_code == 200
        payload = state_response.json()

        phase_feedback = payload.get("phase_feedback", {})
        assert isinstance(phase_feedback, dict)
        # The note is filed under content (the target), not final_review.
        assert "slides repeat; diversify per the research" in (
            phase_feedback.get(PHASE_CONTENT) or []
        )
        assert phase_feedback.get(PHASE_FINAL_REVIEW) in (None, [])
        revision_counts = payload.get("revision_count", {})
        assert int(revision_counts.get(PHASE_CONTENT, 0)) >= 1
        # Images survive a content-only send-back.
        assert payload.get("image_assets") == images


class TestAssignedReviewerPreviewAccess:
    """Scenario: Assigned reviewer can preview draft blog."""

    @pytest.mark.asyncio
    async def test_assigned_reviewer_can_preview_draft_blog(
        self, client: AsyncClient
    ) -> None:
        """Scenario: Assigned reviewer accesses authenticated preview route."""
        owner = await create_user("owner-preview@example.com", UserRole.EDITOR)
        assigned = await create_user("assigned-preview@example.com", UserRole.EDITOR)
        project_id = await create_carousel(owner, is_public=False)
        await seed_workflow_assigned_reviewer(client, project_id, str(assigned.id))

        response = await client.get(
            f"/api/carousels/{project_id}/preview/blog/pt",
            headers=auth_header(assigned),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["markdown"]
