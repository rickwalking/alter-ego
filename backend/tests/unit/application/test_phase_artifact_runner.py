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
    DESIGN_VALIDATION_RECOVERY_HINT,
    PHASE_CONTENT,
    PHASE_DESIGN,
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


def _design_runner() -> PhaseArtifactRunner:
    return PhaseArtifactRunner(
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


def _design_localized_slide(index: int, body_pt: str) -> dict[str, object]:
    return {
        "slide_index": index,
        "slide_type": "hero_content",
        "presentation_pt": {
            "slide_type": "hero_content",
            "heading": f"Titulo {index}",
            "body": body_pt,
        },
        "presentation_en": {
            "slide_type": "hero_content",
            "heading": f"Title {index}",
            "body": f"Body {index}",
        },
    }


@pytest.mark.asyncio
async def test_design_ensure_revalidates_and_advances_validated_at() -> None:
    """Scenario: Plain design revise re-validates instead of looping
    (features/carousel_design_phase_recovery.feature). The design ensure runs
    validate_localized_slides on EVERY execution — validated_at advances past
    the stale stored report and the blocking hint is set."""
    stale_validated_at = "2026-07-07T00:00:00Z"
    state = {
        "project_id": "38affb3e",
        "current_phase": PHASE_DESIGN,
        "localized_slides": [
            _design_localized_slide(1, "Corpo 1"),
            _design_localized_slide(4, "SLIDE 4: rascunho TITLE: pendente"),
        ],
        "presentation_validation": {
            "validation_status": "invalid",
            "validated_at": stale_validated_at,
            "blocking": True,
            "violations": [],
        },
    }

    updates = await _design_runner().ensure_for_phase(state)  # type: ignore[arg-type]

    report = updates["presentation_validation"]
    assert isinstance(report, dict)
    assert report["blocking"] is True
    assert report["validated_at"] != stale_validated_at
    assert any(
        violation["code"] == "drafting_scaffold_present"
        for violation in report["violations"]
    )
    assert updates["design_recovery_hint"] == DESIGN_VALIDATION_RECOVERY_HINT


@pytest.mark.asyncio
async def test_design_ensure_clears_hint_when_validation_passes() -> None:
    """Scenario: Reviewer edits the flagged slide in place at design — after
    a fixing edit, the ensure stores a clean report and clears the hint."""
    state = {
        "project_id": "38affb3e",
        "current_phase": PHASE_DESIGN,
        "localized_slides": [
            _design_localized_slide(1, "Corpo 1"),
            _design_localized_slide(4, "Corpo corrigido do slide quatro."),
        ],
    }

    updates = await _design_runner().ensure_for_phase(state)  # type: ignore[arg-type]

    report = updates["presentation_validation"]
    assert isinstance(report, dict)
    assert report["blocking"] is False
    assert updates["design_recovery_hint"] == ""


@pytest.mark.asyncio
async def test_design_ensure_without_localized_slides_skips_validation() -> None:
    """No localized slides yet — nothing to validate, no report fabricated."""
    state = {
        "project_id": "38affb3e",
        "current_phase": PHASE_DESIGN,
    }

    updates = await _design_runner().ensure_for_phase(state)  # type: ignore[arg-type]

    assert "presentation_validation" not in updates
    assert "design_recovery_hint" not in updates
