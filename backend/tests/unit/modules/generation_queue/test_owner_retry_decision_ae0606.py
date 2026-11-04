"""The owner Retry decision table.

Feature: tests/features/carousel_owner_retry_ae0606.feature
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from rag_backend.modules.generation_queue.domain.owner_retry import (
    AutopilotFacts,
    CarouselRetryState,
    CheckpointFacts,
    QueueFacts,
    RetryFacts,
    RetryKind,
    RetryRefusal,
    decide_retry,
    escalated_run,
)

_OWNER = "owner-1"


_CAROUSEL = CarouselRetryState(
    owner_id=_OWNER,
    assigned_reviewer_id=None,
    topic="Topic",
    phase="content",
    phase_status="failed",
    status="failed",
    workflow_status="draft",
    lock_version=4,
)
_FACTS = RetryFacts(
    actor_id=_OWNER,
    carousel=_CAROUSEL,
    checkpoint=CheckpointFacts(present=True),
    queue=QueueFacts(),
)


def _carousel(**overrides: object) -> CarouselRetryState:
    return replace(_CAROUSEL, **overrides)


def _facts(**overrides: object) -> RetryFacts:
    return replace(_FACTS, **overrides)


def _run(state: str, reason: str | None = None) -> AutopilotFacts:
    return AutopilotFacts(run_id=uuid4(), state=state, reason=reason)


@pytest.mark.unit
class TestAcceptedKinds:
    # Scenario: A failed phase parked before its node is re-driven
    def test_a_parked_failed_phase_is_redriven(self) -> None:
        facts = _facts(checkpoint=CheckpointFacts(present=True, parked=True))
        decision = decide_retry(facts)
        assert decision.kind is RetryKind.REDRIVE
        assert decision.reason == "phase_failed"
        assert decision.refusal is None

    def test_a_failed_phase_with_its_gate_open_is_revised(self) -> None:
        decision = decide_retry(_facts())
        assert decision.kind is RetryKind.REVISE
        assert decision.reason == "phase_failed"

    # Scenario: A blocked content gate is revised with the system retry feedback line
    def test_a_blocked_content_gate_is_revised_naming_the_blocker(self) -> None:
        facts = _facts(
            carousel=_carousel(phase_status="awaiting_human"),
            checkpoint=CheckpointFacts(present=True, blocker="persona_score_too_low"),
        )
        decision = decide_retry(facts)
        assert decision.kind is RetryKind.REVISE
        assert decision.reason == "persona_score_too_low"

    # Scenario: An escalated autopilot run moves back to generating
    def test_an_escalated_gate_is_revised_naming_the_escalation(self) -> None:
        run = _run("escalated", "persona_score_below_threshold")
        facts = _facts(
            carousel=_carousel(phase_status="awaiting_human"),
            checkpoint=CheckpointFacts(present=True, blocker="other"),
            autopilot=run,
        )
        decision = decide_retry(facts)
        assert decision.kind is RetryKind.REVISE
        assert decision.reason == "persona_score_below_threshold"
        assert escalated_run(facts) == run

    def test_an_escalation_without_a_reason_falls_back_to_the_blocker(self) -> None:
        facts = _facts(
            carousel=_carousel(phase_status="awaiting_human"),
            checkpoint=CheckpointFacts(present=True, blocker="blocked"),
            autopilot=_run("escalated"),
        )
        assert decide_retry(facts).reason == "blocked"

    def test_a_parked_open_gate_is_redriven(self) -> None:
        facts = _facts(
            carousel=_carousel(phase_status="awaiting_human", phase="final_review"),
            checkpoint=CheckpointFacts(present=True, parked=True),
        )
        decision = decide_retry(facts)
        assert decision.kind is RetryKind.REDRIVE
        assert decision.reason == "gate_blocked"

    # Scenario: Retry on a rejected carousel re-runs the phase it was rejected at
    def test_a_rejected_gate_is_revised(self) -> None:
        facts = _facts(carousel=_carousel(phase_status="rejected"))
        decision = decide_retry(facts)
        assert decision.kind is RetryKind.REVISE
        assert decision.reason == "carousel_rejected"

    def test_a_rejected_parked_phase_is_redriven(self) -> None:
        facts = _facts(
            carousel=_carousel(phase_status="rejected"),
            checkpoint=CheckpointFacts(present=True, parked=True),
        )
        assert decide_retry(facts).kind is RetryKind.REDRIVE

    # Scenario: Retry on a carousel rejected at the final review reopens the review
    def test_a_rejected_final_review_is_reopened(self) -> None:
        facts = _facts(
            carousel=_carousel(phase_status="rejected", phase="final_review")
        )
        decision = decide_retry(facts)
        assert decision.kind is RetryKind.REOPEN
        assert decision.reason == "carousel_rejected"

    def test_a_pending_parked_phase_is_redriven(self) -> None:
        facts = _facts(
            carousel=_carousel(phase_status="pending"),
            checkpoint=CheckpointFacts(present=True, parked=True),
        )
        assert decide_retry(facts).kind is RetryKind.REDRIVE

    # Scenario: A closed autopilot run leaves the run alone and re-runs the carousel only
    def test_a_closed_run_does_not_block_and_is_not_moved(self) -> None:
        facts = _facts(
            carousel=_carousel(phase_status="rejected"),
            autopilot=_run("rejected", "escalation_expired"),
        )
        assert decide_retry(facts).kind is RetryKind.REVISE
        assert escalated_run(facts) is None


@pytest.mark.unit
class TestRefusals:
    # Scenario: A tap from someone who does not own the carousel changes nothing
    def test_a_non_owner_is_refused_first(self) -> None:
        facts = _facts(actor_id="stranger", queue=QueueFacts(active_run=True))
        assert decide_retry(facts).refusal is RetryRefusal.NOT_OWNER

    def test_a_carousel_without_an_owner_is_refused(self) -> None:
        facts = _facts(carousel=_carousel(owner_id=None))
        assert decide_retry(facts).refusal is RetryRefusal.NOT_OWNER

    def test_another_assigned_reviewer_is_refused(self) -> None:
        facts = _facts(carousel=_carousel(assigned_reviewer_id="reviewer-2"))
        assert decide_retry(facts).refusal is RetryRefusal.NOT_ASSIGNED_REVIEWER

    def test_the_owner_as_assigned_reviewer_is_accepted(self) -> None:
        facts = _facts(carousel=_carousel(assigned_reviewer_id=_OWNER))
        assert decide_retry(facts).kind is RetryKind.REVISE

    # Scenario: A double tap ends in run_in_progress
    def test_an_in_progress_carousel_is_refused(self) -> None:
        facts = _facts(carousel=_carousel(phase_status="in_progress"))
        assert decide_retry(facts).refusal is RetryRefusal.RUN_IN_PROGRESS

    def test_an_active_generation_run_is_refused(self) -> None:
        facts = _facts(queue=QueueFacts(active_run=True, latest_dead_letter=True))
        assert decide_retry(facts).refusal is RetryRefusal.RUN_IN_PROGRESS

    # Scenario: An artifact mutation in progress refuses the retry
    def test_a_held_artifact_lock_is_refused(self) -> None:
        facts = _facts(queue=QueueFacts(mutation_locked=True))
        assert decide_retry(facts).refusal is RetryRefusal.MUTATION_IN_PROGRESS

    # Scenario: A running autopilot run answers autopilot_active
    @pytest.mark.parametrize("state", ["queued", "generating", "reworking"])
    def test_a_driven_autopilot_run_is_refused(self, state: str) -> None:
        facts = _facts(autopilot=_run(state))
        assert decide_retry(facts).refusal is RetryRefusal.AUTOPILOT_ACTIVE

    # Scenario: A queue dead letter answers use_reprocess
    def test_a_latest_dead_letter_of_a_parked_run_is_refused(self) -> None:
        facts = _facts(
            queue=QueueFacts(latest_dead_letter=True),
            autopilot=_run("escalated", "queue_dead_letter:timeout"),
        )
        assert decide_retry(facts).refusal is RetryRefusal.USE_REPROCESS

    def test_a_latest_dead_letter_without_a_run_is_refused(self) -> None:
        facts = _facts(queue=QueueFacts(latest_dead_letter=True))
        assert decide_retry(facts).refusal is RetryRefusal.USE_REPROCESS

    # Scenario: A discarded dead letter no longer blocks the retry
    def test_a_discarded_dead_letter_is_retried(self) -> None:
        facts = _facts(
            queue=QueueFacts(latest_dead_letter=True),
            autopilot=_run("rejected", "owner_queue_discard"),
        )
        assert decide_retry(facts).kind is RetryKind.REVISE

    def test_an_older_dead_letter_does_not_block(self) -> None:
        facts = _facts(autopilot=_run("escalated", "queue_dead_letter:timeout"))
        assert decide_retry(facts).kind is RetryKind.REVISE

    # Scenario: A revise at the revision cap is refused
    def test_a_capped_revise_is_refused(self) -> None:
        facts = _facts(checkpoint=CheckpointFacts(present=True, revise_capped=True))
        assert decide_retry(facts).refusal is RetryRefusal.REVISION_CAP_EXCEEDED

    def test_a_capped_phase_can_still_be_redriven(self) -> None:
        facts = _facts(
            checkpoint=CheckpointFacts(present=True, parked=True, revise_capped=True)
        )
        assert decide_retry(facts).kind is RetryKind.REDRIVE

    # Scenario: An approved or published carousel is not retryable
    @pytest.mark.parametrize(
        "overrides",
        [
            {"phase": "published"},
            {"workflow_status": "approved_for_publish"},
            {"phase_status": "approved"},
        ],
    )
    def test_a_finished_carousel_is_not_retryable(
        self, overrides: dict[str, str]
    ) -> None:
        facts = _facts(carousel=_carousel(**overrides))
        assert decide_retry(facts).refusal is RetryRefusal.NOT_RETRYABLE

    # Scenario: A carousel without a checkpoint is refused with no_checkpoint
    def test_a_missing_checkpoint_is_refused(self) -> None:
        facts = _facts(
            carousel=_carousel(phase_status="rejected"),
            checkpoint=CheckpointFacts(present=False),
        )
        assert decide_retry(facts).refusal is RetryRefusal.NO_CHECKPOINT

    # Scenario: A clean gate with no escalation is not retryable
    def test_a_clean_gate_is_not_retryable(self) -> None:
        facts = _facts(carousel=_carousel(phase_status="awaiting_human"))
        decision = decide_retry(facts)
        assert decision.refusal is RetryRefusal.NOT_RETRYABLE
        assert decision.kind is None

    @pytest.mark.parametrize("status", ["failed", "awaiting_human"])
    def test_the_live_final_review_is_not_retryable(self, status: str) -> None:
        facts = _facts(carousel=_carousel(phase="final_review", phase_status=status))
        assert decide_retry(facts).refusal is RetryRefusal.NOT_RETRYABLE

    def test_a_pending_phase_that_is_not_parked_is_not_retryable(self) -> None:
        facts = _facts(carousel=_carousel(phase_status="pending"))
        assert decide_retry(facts).refusal is RetryRefusal.NOT_RETRYABLE

    def test_guards_run_in_order(self) -> None:
        base = _facts(
            carousel=_carousel(phase="published"),
            checkpoint=CheckpointFacts(present=False),
        )
        assert decide_retry(base).refusal is RetryRefusal.NOT_RETRYABLE
        assert (
            decide_retry(replace(base, queue=QueueFacts(mutation_locked=True))).refusal
            is RetryRefusal.MUTATION_IN_PROGRESS
        )
