"""AE-0405: the feedback-note lifecycle (pure state functions + persistence).

Gherkin: tests/features/content_feedback_lifecycle_ae0405.feature
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest

from rag_backend.agents.carousel_content_park import parked_content_updates
from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel.content_feedback_lifecycle import (
    NewFeedbackNote,
    active_feedback_notes,
    add_feedback_note,
    consume_feedback_notes,
    feedback_history,
    settle_stale_content_feedback,
)
from rag_backend.application.services.carousel.editorial_workflow_feedback import (
    persist_phase_feedback,
    settle_feedback_before_resume,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    PhaseFeedbackPersistParams,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    INTERRUPT_TYPE_CONTENT_REVIEW,
    INTERRUPT_TYPE_DESIGN_REVIEW,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_SOURCE_AUTOPILOT,
    FEEDBACK_SOURCE_HUMAN,
    FEEDBACK_STATUS_APPLIED,
    FEEDBACK_STATUS_DROPPED,
    FEEDBACK_STATUS_MIGRATED,
    PAYLOAD_KEY_PARKED_ARTIFACTS,
    STATE_FIELD_CONTENT_ARTIFACTS_PARKED,
    STATE_FIELD_FEEDBACK_HISTORY,
    STATE_FIELD_FEEDBACK_NOTES,
)

OWNER_NOTE = "Thesis: agents need guardrails, not more autonomy."
STALE_AUTOPILOT = (
    "The content gate failed the autopilot check. "
    "Reason: persona_score_below_threshold. Measured: 5.8."
)


def _state(**values: object) -> CarouselWorkflowState:
    base: dict[str, object] = {
        "project_id": "98a2e2f0",
        "current_phase": PHASE_CONTENT,
        "phase_status": PHASE_STATUS_AWAITING_HUMAN,
    }
    return cast(CarouselWorkflowState, {**base, **values})


def _merge(
    state: CarouselWorkflowState, updates: dict[str, object]
) -> CarouselWorkflowState:
    return cast(CarouselWorkflowState, {**state, **updates})


def _with_note(
    state: CarouselWorkflowState, note: str, source: str = FEEDBACK_SOURCE_HUMAN
) -> CarouselWorkflowState:
    new = NewFeedbackNote(phase=PHASE_CONTENT, note=note, source=source)
    return _merge(state, add_feedback_note(state, new))


def _legacy_98a2e2f0() -> CarouselWorkflowState:
    """The prod checkpoint: three untagged content notes and drafts."""
    return _state(
        phase_feedback={PHASE_CONTENT: [OWNER_NOTE, STALE_AUTOPILOT, OWNER_NOTE]},
        slide_drafts=[{"slide_index": 1, "draft_text": "x"}],
    )


@pytest.mark.unit
class TestAddAndConsume:
    def test_note_is_tagged_with_source_and_time(self) -> None:
        """Scenario: Autopilot gate feedback is tagged (AC4)."""
        state = _with_note(_state(), STALE_AUTOPILOT, FEEDBACK_SOURCE_AUTOPILOT)

        assert active_feedback_notes(state, PHASE_CONTENT) == [STALE_AUTOPILOT]
        tags = cast(dict[str, list[dict[str, str]]], state[STATE_FIELD_FEEDBACK_NOTES])
        assert tags[PHASE_CONTENT][0]["source"] == FEEDBACK_SOURCE_AUTOPILOT
        assert tags[PHASE_CONTENT][0]["added_at"]

    def test_consume_moves_every_active_note_to_history(self) -> None:
        """Scenario: A feedback revise ... moves the note to history (AC1)."""
        state = _with_note(
            _state(phase_feedback={PHASE_CONTENT: ["legacy"]}), OWNER_NOTE
        )

        state = _merge(state, consume_feedback_notes(state, PHASE_CONTENT))

        assert active_feedback_notes(state, PHASE_CONTENT) == []
        history = feedback_history(state, PHASE_CONTENT)
        assert [(e["note"], e["status"]) for e in history] == [
            ("legacy", FEEDBACK_STATUS_APPLIED),
            (OWNER_NOTE, FEEDBACK_STATUS_APPLIED),
        ]
        assert history[0]["added_at"] == ""
        assert all(entry["settled_at"] for entry in history)

    def test_consume_without_notes_changes_nothing(self) -> None:
        assert consume_feedback_notes(_state(), PHASE_CONTENT) == {}

    def test_other_phases_are_untouched(self) -> None:
        state = _state(phase_feedback={PHASE_DESIGN: ["darker"], PHASE_CONTENT: ["x"]})

        updates = consume_feedback_notes(state, PHASE_CONTENT)

        texts = cast(dict[str, list[str]], updates["phase_feedback"])
        assert texts == {PHASE_DESIGN: ["darker"], PHASE_CONTENT: []}

    def test_duplicate_texts_keep_their_own_tags(self) -> None:
        state = _with_note(_with_note(_state(), OWNER_NOTE), OWNER_NOTE)

        state = _merge(state, consume_feedback_notes(state, PHASE_CONTENT))

        assert [e["note"] for e in feedback_history(state, PHASE_CONTENT)] == [
            OWNER_NOTE,
            OWNER_NOTE,
        ]


@pytest.mark.unit
class TestSettleStale:
    def test_legacy_notes_migrate_to_history(self) -> None:
        """Scenario: Legacy notes that predate the last regeneration move to history."""
        state = _legacy_98a2e2f0()

        state = _merge(
            state, settle_stale_content_feedback(state, REVIEW_ACTION_APPROVE)
        )

        assert active_feedback_notes(state, PHASE_CONTENT) == []
        history = feedback_history(state, PHASE_CONTENT)
        assert [e["status"] for e in history] == [FEEDBACK_STATUS_MIGRATED] * 3
        assert [e["note"] for e in history] == [OWNER_NOTE, STALE_AUTOPILOT, OWNER_NOTE]

    def test_legacy_notes_of_a_failed_regeneration_stay_active(self) -> None:
        """Scenario: Legacy notes of a failed regeneration stay active."""
        state = _state(
            phase_status=PHASE_STATUS_FAILED,
            phase_feedback={PHASE_CONTENT: [OWNER_NOTE]},
        )

        assert settle_stale_content_feedback(state, REVIEW_ACTION_REVISE) == {}

    def test_active_autopilot_note_is_dropped_when_content_is_approved(self) -> None:
        """Scenario: An active autopilot note is dropped when the content gate passes."""
        state = _with_note(_state(), STALE_AUTOPILOT, FEEDBACK_SOURCE_AUTOPILOT)
        state = _with_note(state, OWNER_NOTE)

        state = _merge(
            state, settle_stale_content_feedback(state, REVIEW_ACTION_APPROVE)
        )

        assert active_feedback_notes(state, PHASE_CONTENT) == [OWNER_NOTE]
        history = feedback_history(state, PHASE_CONTENT)
        assert [(e["source"], e["status"]) for e in history] == [
            (FEEDBACK_SOURCE_AUTOPILOT, FEEDBACK_STATUS_DROPPED)
        ]

    @pytest.mark.parametrize(
        ("action", "phase"),
        [(REVIEW_ACTION_REVISE, PHASE_CONTENT), (REVIEW_ACTION_APPROVE, PHASE_DESIGN)],
    )
    def test_tagged_autopilot_note_kept_otherwise(
        self, action: str, phase: str
    ) -> None:
        state = _with_note(
            _state(current_phase=phase), STALE_AUTOPILOT, FEEDBACK_SOURCE_AUTOPILOT
        )

        assert settle_stale_content_feedback(state, action) == {}

    def test_malformed_feedback_fields_are_ignored(self) -> None:
        """Scenario: ... malformed history entries are skipped (AC6)."""
        state = _state(
            phase_feedback={PHASE_CONTENT: "not-a-list"},
            **{
                STATE_FIELD_FEEDBACK_NOTES: {PHASE_CONTENT: [7, {"note": 3}]},
                STATE_FIELD_FEEDBACK_HISTORY: {
                    PHASE_CONTENT: [
                        "bad",
                        {"note": OWNER_NOTE, "status": FEEDBACK_STATUS_APPLIED},
                    ]
                },
            },
        )

        assert active_feedback_notes(state, PHASE_CONTENT) == []
        assert settle_stale_content_feedback(state, REVIEW_ACTION_APPROVE) == {}
        [entry] = feedback_history(state, PHASE_CONTENT)
        assert entry["note"] == OWNER_NOTE
        assert entry["source"] == FEEDBACK_SOURCE_HUMAN
        assert entry["settled_at"] == ""
        assert feedback_history(_state(), PHASE_CONTENT) == []
        assert feedback_history(_state(**{STATE_FIELD_FEEDBACK_HISTORY: []}), "x") == []


def _engine() -> CarouselWorkflowEngine:
    engine = AsyncMock(spec=CarouselWorkflowEngine)
    return cast(CarouselWorkflowEngine, engine)


@pytest.mark.unit
@pytest.mark.asyncio
class TestPersistence:
    async def test_persist_tags_the_note_source(self) -> None:
        engine = _engine()

        await persist_phase_feedback(
            engine,
            PhaseFeedbackPersistParams(
                project_id="p",
                prior=_state(),
                feedback=f"  {STALE_AUTOPILOT} ",
                source=FEEDBACK_SOURCE_AUTOPILOT,
            ),
        )

        update = cast(AsyncMock, engine.update_state).await_args
        assert update is not None
        values = cast(dict[str, object], update.args[1])
        assert values["phase_feedback"] == {PHASE_CONTENT: [STALE_AUTOPILOT]}
        assert values["revision_count"] == {PHASE_CONTENT: 1}
        tags = cast(dict[str, list[dict[str, str]]], values[STATE_FIELD_FEEDBACK_NOTES])
        assert tags[PHASE_CONTENT][0]["source"] == FEEDBACK_SOURCE_AUTOPILOT

    async def test_settle_before_resume_writes_only_when_needed(self) -> None:
        engine = _engine()

        unchanged = await settle_feedback_before_resume(
            engine, _state(), REVIEW_ACTION_APPROVE
        )
        settled = await settle_feedback_before_resume(
            engine, _legacy_98a2e2f0(), REVIEW_ACTION_APPROVE
        )

        assert unchanged == _state()
        assert active_feedback_notes(settled, PHASE_CONTENT) == []
        cast(AsyncMock, engine.update_state).assert_awaited_once()


def _snapshot(
    values: dict[str, object], *payloads: dict[str, object]
) -> SimpleNamespace:
    interrupts = tuple(SimpleNamespace(value=payload) for payload in payloads)
    return SimpleNamespace(values=values, interrupts=interrupts, tasks=())


@pytest.mark.unit
class TestParkedContentUpdates:
    def test_parked_content_artifacts_are_saved_with_marker(self) -> None:
        artifacts = {"slide_drafts": [{"slide_index": 1}]}
        snapshot = _snapshot(
            {"content_approved": True},
            {"type": INTERRUPT_TYPE_DESIGN_REVIEW},
            {
                "type": INTERRUPT_TYPE_CONTENT_REVIEW,
                PAYLOAD_KEY_PARKED_ARTIFACTS: artifacts,
            },
        )

        assert parked_content_updates(snapshot) == {
            **artifacts,
            STATE_FIELD_CONTENT_ARTIFACTS_PARKED: True,
            "content_approved": False,
            # AE-0413: the parked checkpoint names the content gate.
            "current_phase": "content",
        }

    @pytest.mark.parametrize(
        "snapshot",
        [
            None,
            SimpleNamespace(values=None),
            _snapshot(
                {STATE_FIELD_CONTENT_ARTIFACTS_PARKED: True},
                {
                    "type": INTERRUPT_TYPE_CONTENT_REVIEW,
                    PAYLOAD_KEY_PARKED_ARTIFACTS: {"slide_drafts": []},
                },
            ),
            _snapshot({}, {"type": INTERRUPT_TYPE_CONTENT_REVIEW}),
            _snapshot(
                {},
                {
                    "type": INTERRUPT_TYPE_CONTENT_REVIEW,
                    PAYLOAD_KEY_PARKED_ARTIFACTS: {},
                },
            ),
            _snapshot(
                {},
                {
                    "type": INTERRUPT_TYPE_DESIGN_REVIEW,
                    PAYLOAD_KEY_PARKED_ARTIFACTS: {"a": 1},
                },
            ),
        ],
    )
    def test_nothing_to_save(self, snapshot: object) -> None:
        assert parked_content_updates(snapshot) is None
