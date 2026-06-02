"""Unit tests for editorial workflow support helpers.

Feature: carousel_pipeline_consolidation.feature (@cp-sse, @cp-feedback)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.carousel.editorial_workflow_support import (
    PhaseFeedbackPersistParams,
    build_progress_event,
    format_sse_event,
    persist_phase_feedback,
    read_checkpoint_phase,
    resolve_background_resume_sse_error_message,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    ERR_WORKFLOW_PHASE_FAILED,
)


@pytest.mark.unit
class TestFormatSseEvent:
    """Scenario: Stream emits progress during in_progress."""

    def test_format_sse_event_includes_event_type_and_data(self) -> None:
        payload = build_progress_event(
            "project-1",
            "images",
            {"phase": "images", "label": "Generating images", "current": 1, "total": 5},
        )
        frame = format_sse_event(payload, event_id=7)

        assert frame.startswith("id: 7\n")
        assert "event: progress\n" in frame
        assert '"phase": "images"' in frame
        assert '"phase_progress"' in frame
        assert frame.endswith("\n")

    def test_format_sse_event_defaults_to_phase_change(self) -> None:
        frame = format_sse_event({"phase": "research"})
        assert "event: phase_change\n" in frame


@pytest.mark.unit
class TestPersistPhaseFeedback:
    """Scenario: Stored feedback is passed to regeneration on revise."""

    async def test_persist_phase_feedback_appends_and_increments_revision(self) -> None:
        engine = MagicMock()
        engine.update_state = AsyncMock()
        prior = {
            "current_phase": "content",
            "phase_feedback": {"content": ["First note"]},
            "revision_count": {"content": 1},
        }

        await persist_phase_feedback(
            engine,
            PhaseFeedbackPersistParams(
                project_id="project-1",
                prior=prior,
                feedback="Slide 2 tone is too formal",
            ),
        )

        engine.update_state.assert_awaited_once()
        update = engine.update_state.await_args.args[1]
        assert update["phase_feedback"]["content"] == [
            "First note",
            "Slide 2 tone is too formal",
        ]
        assert update["revision_count"]["content"] == 2

    async def test_persist_phase_feedback_skips_empty_feedback(self) -> None:
        engine = MagicMock()
        engine.update_state = AsyncMock()

        await persist_phase_feedback(
            engine,
            PhaseFeedbackPersistParams(
                project_id="project-1",
                prior={"current_phase": "content"},
                feedback="  ",
            ),
        )

        engine.update_state.assert_not_awaited()


@pytest.mark.unit
class TestReadCheckpointPhase:
    """Scenario: Structured feedback gate reads checkpoint phase."""

    async def test_read_checkpoint_phase_returns_checkpoint_value(self) -> None:
        engine = MagicMock()
        engine._run_config = MagicMock(
            return_value={"configurable": {"thread_id": "t"}}
        )
        snapshot = MagicMock()
        snapshot.values = {"current_phase": "final_review"}
        engine._app.aget_state = AsyncMock(return_value=snapshot)

        phase = await read_checkpoint_phase(engine, "project-1")

        assert phase == "final_review"


@pytest.mark.unit
class TestResolveBackgroundResumeSseErrorMessage:
    """Scenario: Background resume failures publish client-safe SSE errors."""

    def test_maps_known_validation_errors(self) -> None:
        assert (
            resolve_background_resume_sse_error_message(ERR_REVISION_CAP_EXCEEDED)
            == ERR_REVISION_CAP_EXCEEDED
        )
        assert (
            resolve_background_resume_sse_error_message(ERR_PERSONA_SCORE_TOO_LOW)
            == ERR_PERSONA_SCORE_TOO_LOW
        )

    def test_redacts_internal_exception_text(self) -> None:
        assert (
            resolve_background_resume_sse_error_message("content generation failed")
            == ERR_BACKGROUND_RESUME_FAILED
        )
        assert (
            resolve_background_resume_sse_error_message(ERR_WORKFLOW_PHASE_FAILED)
            == ERR_WORKFLOW_PHASE_FAILED
        )
