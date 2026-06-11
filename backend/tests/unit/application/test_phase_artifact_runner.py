"""Unit tests for PhaseArtifactRunner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_OUTLINE,
    PHASE_STATUS_FAILED,
    WORKFLOW_ERROR_KEY,
)


@pytest.mark.asyncio
async def test_invalid_content_json_marks_workflow_failed() -> None:
    """Scenario: Invalid content JSON fails loudly without stub slide."""
    runner = PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=MagicMock(),
            workflow_input=EditorialWorkflowStartInput(
                topic="Topic",
                audience="Audience",
                brief="Brief",
                sources=[],
            ),
        )
    )
    state = {
        "project_id": "project-1",
        "current_phase": PHASE_CONTENT,
        "outline": [{"slide_index": 1, "title": "Intro", "key_points": []}],
    }

    with patch(
        "rag_backend.application.services.carousel.phase_artifact_runner.generate_slide_drafts",
        new=AsyncMock(side_effect=ValueError(ERR_INVALID_JSON)),
    ):
        updates = await runner.ensure_for_phase(state)  # type: ignore[arg-type]

    assert updates[WORKFLOW_ERROR_KEY] == ERR_INVALID_JSON
    assert updates["phase_status"] == PHASE_STATUS_FAILED


@pytest.mark.asyncio
async def test_outline_artifact_publishes_sse_update() -> None:
    """Scenario: Generated outline artifacts publish incremental SSE updates."""
    runner = PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=MagicMock(),
            workflow_input=EditorialWorkflowStartInput(
                topic="Topic",
                audience="Audience",
                brief="Brief",
                sources=[],
            ),
        )
    )
    state = {
        "project_id": "project-1",
        "current_phase": PHASE_OUTLINE,
    }
    outline = [{"slide_index": 1, "title": "Intro"}]

    with (
        patch(
            "rag_backend.application.services.carousel.phase_artifact_runner.generate_outline",
            new=AsyncMock(return_value=outline),
        ),
        patch(
            "rag_backend.application.services.carousel.phase_artifact_runner.publish_workflow_artifacts_from_updates",
            new=AsyncMock(),
        ) as publish_mock,
    ):
        updates = await runner.ensure_for_phase(state)  # type: ignore[arg-type]

    assert updates["outline"] == outline
    publish_mock.assert_awaited_once_with(
        "project-1", PHASE_OUTLINE, {"outline": outline}
    )
