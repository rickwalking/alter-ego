"""The dashboard resume only queues work; the generation worker runs it."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

import rag_backend.infrastructure.database.config as db_config
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.models import UserRole
from rag_backend.modules.generation_queue.domain.models import WorkflowResumePayload
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.carousel_consolidation.helpers import (
    auth_header,
    create_carousel,
    create_user,
    get_lock_version,
    seed_workflow_phase,
)


async def _generation_rows() -> list[GenerationRunModel]:
    async with db_config.get_session_maker()() as session:
        return list((await session.scalars(select(GenerationRunModel))).all())


@pytest.mark.asyncio
async def test_resume_queues_one_run_and_runs_nothing(client: AsyncClient) -> None:
    """Scenario: The dashboard resume is queued, not run in the web process"""
    editor = await create_user("queued-resume@example.com", UserRole.EDITOR)
    project_id = await create_carousel(editor, is_public=False)
    await seed_workflow_phase(
        client,
        project_id,
        phase=PHASE_RESEARCH,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        extra_state={"research_findings": [{"title": "F", "summary": "D"}]},
    )
    version = await get_lock_version(project_id)

    response = await client.post(
        f"/api/carousels/{project_id}/workflow/resume",
        json={"action": "revise", "feedback": "shorter", "expected_version": version},
        headers=auth_header(editor),
    )

    assert response.status_code == 202
    (row,) = await _generation_rows()
    assert row.kind == "workflow_resume"
    assert row.status == "queued"
    assert row.carousel_project_id == project_id
    assert row.dedupe_key == f"resume:{project_id}:{version + 1}"
    payload = WorkflowResumePayload.parse(row.payload)
    assert payload.action == "revise"
    assert payload.feedback == "shorter"
    assert payload.reviewer_id == str(editor.id)
    state = await client.get(
        f"/api/carousels/{project_id}/workflow/state", headers=auth_header(editor)
    )
    assert state.json()["phase_status"] == PHASE_STATUS_IN_PROGRESS
    assert state.json()["current_phase"] == PHASE_RESEARCH
