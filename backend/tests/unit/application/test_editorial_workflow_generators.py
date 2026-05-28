"""Unit tests for editorial workflow generators."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.carousel.editorial_workflow_generators import (
    generate_slide_drafts,
)


@pytest.mark.asyncio
async def test_generate_slide_drafts_includes_revision_notes_in_persona_context() -> (
    None
):
    """Scenario: Stored feedback is passed to regeneration on revise."""
    content_agent = MagicMock()
    content_agent.draft_slide = AsyncMock(return_value={"draft_text": "Draft"})

    await generate_slide_drafts(
        content_agent,
        [{"slide_index": 1, "title": "Intro", "key_points": ["Point"]}],
        persona=None,
        revision_notes=["Slide 2 tone is too formal"],
    )

    kwargs = content_agent.draft_slide.await_args.kwargs
    assert "Slide 2 tone is too formal" in kwargs["persona_context"]
