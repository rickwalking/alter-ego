"""Unit tests for editorial workflow generators."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.carousel.editorial_workflow_generators import (
    SlideDraftGenerationParams,
    generate_slide_drafts,
)


@pytest.mark.asyncio
async def test_generate_slide_drafts_passes_revision_notes_not_persona_context() -> (
    None
):
    """AE-0291 dedup: reviewer notes flow via revision_notes (rendered imperatively
    in the instruction context), NOT duplicated into persona_context."""
    content_agent = MagicMock()
    content_agent.draft_slide = AsyncMock(return_value={"draft_text": "Draft"})

    await generate_slide_drafts(
        content_agent,
        SlideDraftGenerationParams(
            outline=[{"slide_index": 1, "title": "Intro", "key_points": ["Point"]}],
            revision_notes=["Slide 2 tone is too formal"],
        ),
    )

    kwargs = content_agent.draft_slide.await_args.kwargs
    assert "Slide 2 tone is too formal" in kwargs["revision_notes"]
    assert "Slide 2 tone is too formal" not in kwargs["persona_context"]


def _outline() -> list[dict[str, object]]:
    return [
        {"slide_index": 1, "title": "Intro", "key_points": ["hook"]},
        {"slide_index": 2, "title": "Origins", "key_points": ["history"]},
        {"slide_index": 3, "title": "Impact", "key_points": ["outcome"]},
    ]


@pytest.mark.asyncio
async def test_sibling_context_excludes_self_and_includes_others() -> None:
    """AE-0291: each slide sees the OTHER slides' outline, never its own."""
    content_agent = MagicMock()
    content_agent.draft_slide = AsyncMock(
        side_effect=[
            {"draft_text": "alpha compute scaling"},
            {"draft_text": "bravo governance policy"},
            {"draft_text": "charlie open ecosystems"},
        ]
    )

    await generate_slide_drafts(
        content_agent, SlideDraftGenerationParams(outline=_outline())
    )

    first_call = content_agent.draft_slide.await_args_list[0].kwargs
    sibling = first_call["sibling_context"]
    assert "Origins" in sibling and "Impact" in sibling
    assert "Intro" not in sibling


@pytest.mark.asyncio
async def test_previous_draft_mapped_by_slide_index() -> None:
    """AE-0291: the prior rejected body is fed back for the matching slide index."""
    content_agent = MagicMock()
    content_agent.draft_slide = AsyncMock(
        side_effect=[
            {"draft_text": "fresh alpha"},
            {"draft_text": "fresh bravo"},
            {"draft_text": "fresh charlie"},
        ]
    )

    await generate_slide_drafts(
        content_agent,
        SlideDraftGenerationParams(
            outline=_outline(),
            previous_drafts=[{"slide_index": 2, "draft_text": "old bravo copy"}],
        ),
    )

    calls = {
        c.kwargs["slide_index"]: c.kwargs
        for c in content_agent.draft_slide.await_args_list
    }
    assert calls[2]["previous_draft"] == "old bravo copy"
    assert calls[1]["previous_draft"] == ""


@pytest.mark.asyncio
async def test_bounded_redraft_runs_once_for_duplicate_and_keeps_distinct() -> None:
    """AE-0291: a near-duplicate slide is re-drafted exactly once; the more distinct
    result is kept (redraft count is bounded, no unbounded loop)."""
    content_agent = MagicMock()
    duplicate = "vulnerability discovery is a national security risk for nations"
    content_agent.draft_slide = AsyncMock(
        side_effect=[
            {"draft_text": duplicate},
            {"draft_text": duplicate + " today"},  # slide 2 ~ duplicate of slide 1
            {"draft_text": "open weight parity reshapes the landscape entirely"},
            {"draft_text": "totally different rewritten copy about latency budgets"},
        ]
    )

    drafts = await generate_slide_drafts(
        content_agent, SlideDraftGenerationParams(outline=_outline())
    )

    # 3 initial + exactly 1 bounded re-draft for the flagged duplicate.
    assert content_agent.draft_slide.await_count == 4
    assert drafts[1]["draft_text"] == (
        "totally different rewritten copy about latency budgets"
    )
