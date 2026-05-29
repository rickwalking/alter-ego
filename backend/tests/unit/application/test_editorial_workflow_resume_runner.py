"""Unit tests for background editorial workflow resume runner helpers."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.editorial_workflow_support import (
    resolve_background_resume_sse_error_message,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_PERSONA_SCORE_TOO_LOW,
)


@pytest.mark.unit
class TestBackgroundResumeErrorAllowlist:
    """Scenario: Background resume failure publishes recoverable error event."""

    def test_internal_runtime_errors_are_redacted(self) -> None:
        assert (
            resolve_background_resume_sse_error_message("content generation failed")
            == ERR_BACKGROUND_RESUME_FAILED
        )

    def test_known_persona_errors_pass_through(self) -> None:
        assert (
            resolve_background_resume_sse_error_message(ERR_PERSONA_SCORE_TOO_LOW)
            == ERR_PERSONA_SCORE_TOO_LOW
        )
