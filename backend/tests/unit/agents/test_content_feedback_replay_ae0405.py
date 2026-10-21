"""Content revision notes steer one regeneration; edits never regenerate.

Gherkin: tests/features/content_feedback_lifecycle_ae0405.feature

Real engine + real artifact runner on an in-memory checkpointer; the drafting
model is a spy (no network). See ``content_feedback_flow_ae0405``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from rag_backend.application.services.carousel.content_feedback_lifecycle import (
    feedback_history,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_STATUS_FAILED,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_SOURCE_AUTOPILOT,
    FEEDBACK_SOURCE_HUMAN,
    FEEDBACK_STATUS_APPLIED,
    STRUCTURED_FEEDBACK_SOURCE_KEY,
)
from tests.unit.agents.content_feedback_flow_ae0405 import (
    GENERATE_TARGET,
    PROJECT_ID,
    DraftingModel,
    Review,
    build_engine,
    drafts_for,
    edited_slide,
    localized_slide,
    manual_fixes,
    park_at_content,
    review,
    state_of,
)

THESIS = "Tighten the thesis"
HOOK = "Shorter hook"
AUTOPILOT_NOTE = (
    "The content gate failed the autopilot check. "
    "Reason: persona_score_below_threshold. Measured: 5.8."
)


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> Iterator[DraftingModel]:
    spy = DraftingModel()
    monkeypatch.setattr(GENERATE_TARGET, spy)
    yield spy


def _revise(note: str) -> Review:
    return Review(action=REVIEW_ACTION_REVISE, feedback=note)


@pytest.mark.unit
@pytest.mark.asyncio
class TestFeedbackReviseLifecycle:
    async def test_revise_regenerates_once_and_moves_note_to_history(
        self, model: DraftingModel
    ) -> None:
        """Scenario: A feedback revise regenerates once and moves the note to history (AC1)."""
        engine = build_engine(model)
        await park_at_content(engine)

        await review(engine, _revise(THESIS))

        state = await state_of(engine)
        assert model.calls == [[], [THESIS]]
        assert state["phase_feedback"][PHASE_CONTENT] == []
        history = feedback_history(state, PHASE_CONTENT)
        assert [(e["note"], e["status"], e["source"]) for e in history] == [
            (THESIS, FEEDBACK_STATUS_APPLIED, FEEDBACK_SOURCE_HUMAN)
        ]
        assert history[0]["added_at"] <= history[0]["settled_at"]
        assert state["current_phase"] == PHASE_CONTENT

    async def test_approve_after_revise_commits_the_reviewed_drafts(
        self, model: DraftingModel
    ) -> None:
        """Scenario: Approving after a feedback revise keeps the reviewed drafts."""
        engine = build_engine(model)
        await park_at_content(engine)
        await review(engine, _revise(THESIS))
        reviewed = (await state_of(engine))["slide_drafts"]

        await review(engine, Review(action=REVIEW_ACTION_APPROVE))

        state = await state_of(engine)
        assert model.calls == [[], [THESIS]]
        assert state["slide_drafts"] == reviewed == drafts_for(2)
        assert state["current_phase"] == PHASE_DESIGN


@pytest.mark.unit
@pytest.mark.asyncio
class TestReplayReuse:
    async def test_resume_replay_reuses_the_parked_artifacts(
        self, model: DraftingModel
    ) -> None:
        """Scenario: The resume on approval does not regenerate (no ensure, no LLM).

        LangGraph replays the content node on every resume; the replay reuses
        the artifacts saved when the graph parked instead of running the ensure
        (persona scoring, fail-closed retry) again.
        """
        engine = build_engine(model)
        await park_at_content(engine)
        assert model.content_ensures == 1

        await review(engine, Review(action=REVIEW_ACTION_APPROVE))

        assert model.content_ensures == 1
        assert model.calls == [[]]

    async def test_revise_replay_reuses_then_reenters_once(
        self, model: DraftingModel
    ) -> None:
        """Scenario: A feedback revise regenerates once (one fresh content entry)."""
        engine = build_engine(model)
        await park_at_content(engine)

        await review(engine, _revise(THESIS))

        assert model.content_ensures == 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestEditsOnly:
    async def test_edits_only_resubmit_keeps_edited_copy_without_drafting(
        self, model: DraftingModel
    ) -> None:
        """Scenario: An edits-only resubmit after a feedback revise keeps the edited copy (AC2).

        Regression (98a2e2f0): old notes present, edits-only resubmit -> the
        drafting model is NOT called and the edited copy is unchanged.
        """
        engine = build_engine(model)
        await park_at_content(engine)
        await review(engine, _revise(THESIS))
        edit = edited_slide(await state_of(engine), 2)

        await review(engine, manual_fixes(edit))

        state = await state_of(engine)
        assert model.calls == [[], [THESIS]]
        assert model.retries == []
        slide = localized_slide(state, 2)
        assert slide["presentation_pt"] == edit["presentation_pt"]
        assert slide["presentation_en"] == edit["presentation_en"]
        assert state["current_phase"] == PHASE_CONTENT

    async def test_new_note_after_edits_regenerates_with_only_that_note(
        self, model: DraftingModel
    ) -> None:
        """Scenario: A new note after an edits-only resubmit regenerates with only that note (AC3)."""
        engine = build_engine(model)
        await park_at_content(engine)
        await review(engine, _revise(THESIS))
        await review(engine, manual_fixes(edited_slide(await state_of(engine), 2)))

        await review(engine, _revise(HOOK))

        assert model.calls == [[], [THESIS], [HOOK]]
        notes = [e["note"] for e in feedback_history(await state_of(engine), "content")]
        assert notes == [THESIS, HOOK]

    async def test_approval_resume_keeps_hand_fixed_slides(
        self, model: DraftingModel
    ) -> None:
        """Scenario: The resume on approval does not regenerate without unapplied notes (AC5)."""
        engine = build_engine(model)
        await park_at_content(engine)
        await review(engine, _revise(THESIS))
        state = await state_of(engine)
        fixes = (edited_slide(state, 3), edited_slide(state, 6))
        await review(engine, manual_fixes(*fixes))

        await review(engine, Review(action=REVIEW_ACTION_APPROVE))

        state = await state_of(engine)
        assert model.calls == [[], [THESIS]]
        assert state["current_phase"] == PHASE_DESIGN
        for fix in fixes:
            index = fix["slide_index"]
            assert isinstance(index, int)
            assert (
                localized_slide(state, index)["presentation_pt"]
                == (fix["presentation_pt"])
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestAutopilotAndFailures:
    async def test_autopilot_note_is_tagged_applied_once_and_not_refed(
        self, model: DraftingModel
    ) -> None:
        """Scenario: Autopilot gate feedback is tagged, applied once and not re-fed (AC4)."""
        engine = build_engine(model)
        await park_at_content(engine)

        await review(
            engine,
            Review(
                action=REVIEW_ACTION_REVISE,
                feedback=AUTOPILOT_NOTE,
                structured={STRUCTURED_FEEDBACK_SOURCE_KEY: FEEDBACK_SOURCE_AUTOPILOT},
            ),
        )
        await review(engine, manual_fixes(edited_slide(await state_of(engine), 2)))
        await review(engine, Review(action=REVIEW_ACTION_APPROVE))

        assert model.calls == [[], [AUTOPILOT_NOTE]]
        history = feedback_history(await state_of(engine), PHASE_CONTENT)
        assert [(e["source"], e["status"]) for e in history] == [
            (FEEDBACK_SOURCE_AUTOPILOT, FEEDBACK_STATUS_APPLIED)
        ]

    async def test_final_review_send_back_regenerates_once_and_regates(
        self, model: DraftingModel
    ) -> None:
        """Scenario: A send-back note regenerates once; the content gate re-opens.

        A stale content_approved=True must not route past the content gate.
        """
        engine = build_engine(model)
        await park_at_content(engine)
        for _ in range(3):
            await review(engine, Review(action=REVIEW_ACTION_APPROVE))

        await review(
            engine,
            Review(
                action=REVIEW_ACTION_REVISE,
                feedback=THESIS,
                structured={STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_CONTENT},
            ),
        )
        await review(engine, manual_fixes(edited_slide(await state_of(engine), 2)))

        state = await state_of(engine)
        assert model.calls == [[], [THESIS]]
        assert state["current_phase"] == PHASE_CONTENT

    async def test_failed_regeneration_keeps_the_note_active(
        self, model: DraftingModel
    ) -> None:
        """Scenario: A regeneration that fails keeps the note active."""
        engine = build_engine(model)
        await park_at_content(engine)
        model.fail_next = True

        await review(engine, _revise(THESIS))

        state = await state_of(engine)
        assert state["phase_status"] == PHASE_STATUS_FAILED
        assert state["phase_feedback"][PHASE_CONTENT] == [THESIS]
        assert feedback_history(state, PHASE_CONTENT) == []
        assert state.get("project_id") == PROJECT_ID
